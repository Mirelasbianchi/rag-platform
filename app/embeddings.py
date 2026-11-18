"""Embedding providers.

`EMBEDDING_MODEL` selects the provider:

- ``local/hashing`` runs fully offline: a deterministic feature-hashing embedding over
  word unigrams, word bigrams and character trigrams. It needs no API key, which makes CI,
  demos and the retrieval benchmark reproducible. It is a lexical baseline, not a semantic
  model.
- any other value is passed to LiteLLM (e.g. ``openai/text-embedding-3-small``).
"""

import hashlib
import itertools
import re
import unicodedata

import numpy as np

LOCAL_HASHING = "local/hashing"

_TOKEN = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase and strip accents so 'Consumidor' and 'consumidor' share features."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _features(text: str) -> list[tuple[str, float]]:
    words = _TOKEN.findall(normalize(text))
    features: list[tuple[str, float]] = [(f"w:{w}", 1.0) for w in words]
    features += [(f"b:{a}_{b}", 0.7) for a, b in itertools.pairwise(words)]
    for w in words:
        padded = f"#{w}#"
        features += [(f"c:{padded[i:i + 3]}", 0.3) for i in range(len(padded) - 2)]
    return features


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
    value = int.from_bytes(digest, "little")
    sign = 1.0 if value & 1 else -1.0
    return (value >> 1) % dim, sign


def hashing_embed(texts: list[str], dim: int) -> list[list[float]]:
    vectors = np.zeros((len(texts), dim), dtype=np.float32)
    for row, text in enumerate(texts):
        for feature, weight in _features(text):
            index, sign = _bucket(feature, dim)
            vectors[row, index] += sign * weight
    # sublinear scaling dampens very frequent features, then L2-normalize for cosine
    vectors = np.sign(vectors) * np.log1p(np.abs(vectors))
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).tolist()


def embed(texts: list[str], model: str, dim: int) -> list[list[float]]:
    if model == LOCAL_HASHING:
        return hashing_embed(texts, dim)
    import litellm  # imported lazily: the offline path does not need it

    response = litellm.embedding(model=model, input=texts)
    return [item["embedding"] for item in response.data]
