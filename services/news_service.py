import re
import feedparser
from datetime import datetime, timezone, timedelta
from cachetools import TTLCache

_cache = TTLCache(maxsize=1, ttl=300)

# Reputable F1 news sources
_FEEDS = [
    {"name": "BBC Sport F1", "url": "https://feeds.bbci.co.uk/sport/formula1/rss.xml"},
    {"name": "Motorsport.com", "url": "https://www.motorsport.com/rss/f1/news/"},
    {"name": "RaceFans", "url": "https://www.racefans.net/feed/"},
    {"name": "Reddit", "url": "https://www.reddit.com/r/formula1.rss"}
]

# Words that indicate low-quality / clickbait articles
_JUNK_KEYWORDS = [
    "secret santa", "wag", "girlfriend", "boyfriend",
    "outfit", "fashion", "instagram", "tiktok",
    "podcast recap", "unboxing", "giveaway",
]

def _parse_date(entry):
    """Extract publication date from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return None


def _is_junk(title):
    """Check if an article title looks like clickbait / irrelevant gossip."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in _JUNK_KEYWORDS)


def get_news():
    """Fetch and filter F1 news from RSS feeds"""
    if "news" in _cache:
        return _cache["news"]
    
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for feed_info in _FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:15]:
                # Parse the date
                publication_date = _parse_date(entry)

                if publication_date and publication_date < cutoff:
                    continue

                title = entry.get("title", "")

                # Ignore JUNK keywords
                if _is_junk(title):
                    continue

                # Clean up summary
                summary = ""
                if entry.get("summary"):
                    summary = re.sub(r"<[^>]+>", "", entry["summary"])[:200]

                articles.append({
                    "title": title,
                    "link": entry.get("link", "#"),
                    "source": feed_info["name"],
                    "date": publication_date.strftime("%d %b %Y, %H:%M") if publication_date else "Unknown",
                    "date_ts": publication_date.timestamp() if publication_date else 0,
                    "summary": summary
                })

        except Exception as e:
            print(f"Error while getting news from {feed_info['name']}: {e}")

    # Sorting by date
    articles.sort(key=lambda x: x["date_ts"], reverse=True)

    _cache["news"] = articles
    return articles