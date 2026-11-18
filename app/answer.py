"""Answer generation with citations.

If `LLM_MODEL` is set, the retrieved chunks are sent to that model through LiteLLM with
instructions to cite them as [1], [2], ... Otherwise an extractive answer is built from the
sentences of the retrieved chunks that best overlap with the question, so the endpoint
works offline too.
"""

import re

from app.embeddings import normalize

SYSTEM_PROMPT = """You answer questions using only the numbered context passages.
Cite every claim with the passage number in square brackets, e.g. [1] or [2][3].
If the passages do not contain the answer, say you could not find it in the documents.
Answer in the language of the question, in at most five sentences."""

_SENTENCE = re.compile(r"(?<=[.;!?])\s+|\n+")
_WORD = re.compile(r"\w+")
STOPWORDS = frozenset({
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "um", "uma", "para", "por", "com", "que", "se", "ao", "aos", "qual", "quais", "quem",
    "como", "quando", "onde", "ser", "sao", "the", "of", "to", "and", "in", "is", "what", "who",
    "how", "when"
})


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall(normalize(text)) if w not in STOPWORDS and len(w) > 2}


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] ({hit['title']})\n{hit['content']}" for i, hit in enumerate(hits, start=1)
    )


def _body(content: str) -> str:
    """Drop the heading-path line that chunk_markdown prepends (it has no sentence end)."""
    first, _, rest = content.partition("\n")
    return rest if rest and not first.rstrip().endswith((".", ";", ":", "?", "!")) else content


def extractive_answer(question: str, hits: list[dict], max_sentences: int = 2) -> str:
    """Pick the sentences that share the most terms with the question, keeping citations."""
    query = _terms(question)
    scored = []
    for n, hit in enumerate(hits, start=1):
        for position, sentence in enumerate(_SENTENCE.split(_body(hit["content"]))):
            terms = _terms(sentence)
            overlap = len(query & terms)
            if overlap:
                # favour focused sentences, then higher-ranked passages, then earlier sentences
                score = overlap / (1 + len(terms)) ** 0.5
                scored.append((score, -n, -position, sentence.strip(), n))
    if not scored:
        return "I could not find the answer in the documents."
    best = sorted(scored, reverse=True)[:max_sentences]
    return " ".join(f"{sentence} [{n}]" for *_, sentence, n in best)


def llm_answer(question: str, hits: list[dict], model: str) -> str:
    import litellm

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{build_context(hits)}\n\nQuestion: {question}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def answer(question: str, hits: list[dict], model: str | None) -> tuple[str, str]:
    """Return (answer, strategy) where strategy is 'llm' or 'extractive'."""
    if model:
        return llm_answer(question, hits, model), "llm"
    return extractive_answer(question, hits), "extractive"
