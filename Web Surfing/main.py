"""
Finds trending / relevant content around a topic using the Exa API.
Later this topic string will be derived from Instagram post metadata
(caption text, hashtags, etc.) instead of being typed manually.
"""

import os
from datetime import datetime, timedelta
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Store your key as an env var: export EXA_API_KEY="your-key-here"
exa = Exa(api_key=os.getenv("EXA_API_KEY"))


# ---------------------------------------------------------------------------
# Core search function
# ---------------------------------------------------------------------------

def find_trending(topic: str, num_results: int = 10, days_back: int = 14):
    """
    Search the web for trending / recent content related to `topic`.

    Args:
        topic: The subject to search for (e.g. "AI coding tools",
               or later, extracted keywords/hashtags from an IG post).
        num_results: How many results to fetch.
        days_back: Only consider content published in the last N days,
                   to keep results "trending" rather than evergreen.

    Returns:
        List of dicts with title, url, published date, and highlights.
    """
    start_date = (datetime.utcnow() - timedelta(days=days_back)
                  ).strftime("%Y-%m-%d")

    result = exa.search_and_contents(
        topic,
        type="auto",
        num_results=num_results,
        start_published_date=start_date,
        highlights={
            "num_sentences": 3,
            "highlights_per_url": 2,
        },
        text=False,  # we only need highlights, not full page text, for now
    )

    parsed = []
    for r in result.results:
        parsed.append({
            "title": r.title,
            "url": r.url,
            "published_date": getattr(r, "published_date", None),
            "score": getattr(r, "score", None),
            "highlights": getattr(r, "highlights", []),
        })

    return parsed


# ---------------------------------------------------------------------------
# Pretty printer (for now — later this feeds a suggestion/LLM step)
# ---------------------------------------------------------------------------

def print_trends(trends):
    if not trends:
        print("No results found.")
        return

    for i, t in enumerate(trends, 1):
        print(f"\n{i}. {t['title']}")
        print(f"   URL: {t['url']}")
        if t["published_date"]:
            print(f"   Published: {t['published_date']}")
        for h in t["highlights"]:
            print(f"   > {h}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # For now, hardcode or take CLI input.
    # Later: this string comes from parsed Instagram post metadata.
    topic = input("Enter a topic to find trends for: ").strip()

    trends = find_trending(topic, num_results=10, days_back=14)
    print_trends(trends)
