"""Load the evaluation corpus into a running API, one document per article.

The corpus is Title I of the Brazilian Consumer Defense Code (Lei 8.078/1990, CDC),
taken from planalto.gov.br. Brazilian statutes are public domain (Lei 9.610/1998, art. 8, IV).

Usage: uv run python eval/ingest_corpus.py --url http://localhost:8000
"""

import argparse
import re
from pathlib import Path

import httpx

CORPUS = Path(__file__).parent / "corpus" / "cdc_titulo_i.txt"
HEADING = re.compile(r"^(CAPÍTULO|SEÇÃO)\s+([\w-]+)\s+(.*)$")
ARTICLE = re.compile(r"^Art\. (\d+(?:-[A-Z])?)")


def parse(text: str) -> list[dict]:
    """Split the code into articles, keeping the chapter and section each belongs to."""
    articles: list[dict] = []
    chapter = section = ""
    for line in text.splitlines():
        if heading := HEADING.match(line):
            kind, number, name = heading.groups()
            if kind == "CAPÍTULO":
                chapter, section = f"Capítulo {number} — {name}", ""
            else:
                section = f"Seção {number} — {name}"
            continue
        if article := ARTICLE.match(line):
            articles.append({"number": article.group(1), "chapter": chapter,
                             "section": section, "lines": [line]})
        elif articles:
            articles[-1]["lines"].append(line)
    return articles


def to_markdown(article: dict) -> str:
    headings = [f"# CDC — {article['chapter']}"]
    if article["section"]:
        headings.append(f"## {article['section']}")
    return "\n\n".join([*headings, "\n".join(article["lines"])])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    articles = parse(CORPUS.read_text())
    with httpx.Client(base_url=args.url, timeout=60) as client:
        for article in articles:
            response = client.post("/documents", json={
                "title": f"CDC Art. {article['number']}",
                "source": f"cdc:art-{article['number'].lower()}",
                "text": to_markdown(article),
            })
            response.raise_for_status()
    print(f"Ingested {len(articles)} articles from {CORPUS.name}")


if __name__ == "__main__":
    main()
