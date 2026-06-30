"""
Reddit Monitor for ToolCompareLabs
Monitors r/shopify and r/ecommerce for high-intent posts,
generates professional replies via DeepSeek API.

Usage:
    python reddit_monitor.py --once          # Run once and exit
    python reddit_monitor.py --watch         # Loop every 5 minutes
    python reddit_monitor.py --test "Klaviyo vs Omnisend for Shopify?"
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone

import requests
from openai import OpenAI

# ============================================================
# Config
# ============================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

SUBREDDITS = ["shopify", "ecommerce"]
KEYWORDS = [
    "klaviyo alternative",
    "omnisend review",
    "omnisend vs",
    "pagefly speed",
    "pagefly vs",
    "shogun vs",
    "shopify email automation",
    "shopify marketing automation",
    "sms marketing shopify",
    "best shopify page builder",
    "shopify app comparison",
]

SITE_URL = "https://toolcomparelabs.com"
ARTICLE_MAP = {
    "omnisend": f"{SITE_URL}/omnisend-vs-klaviyo",
    "klaviyo": f"{SITE_URL}/omnisend-vs-klaviyo",
    "pagefly": f"{SITE_URL}/pagefly-vs-shogun",
    "shogun": f"{SITE_URL}/pagefly-vs-shogun",
    "mailchimp": f"{SITE_URL}/omnisend-email-marketing-sms-vs-mailchimp-email-sms-marketing",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ============================================================
# Reddit API (public JSON, no auth required)
# ============================================================
def fetch_posts(subreddit: str, limit: int = 25) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch r/{subreddit}: {e}")
        return []


def filter_posts(posts: list[dict], keywords: list[str]) -> list[dict]:
    hits = []
    for child in posts:
        post = child.get("data", {})
        title = (post.get("title") or "").lower()
        selftext = (post.get("selftext") or "").lower()
        combined = title + " " + selftext

        for kw in keywords:
            if kw.lower() in combined:
                hits.append(post)
                break
    return hits


# ============================================================
# LLM Reply Generator
# ============================================================
def _detect_topic(title: str, body: str) -> tuple[str, str, str]:
    """Detect which apps are being discussed and return the best article link."""
    text = (title + " " + body).lower()
    apps_found = []
    for app in ARTICLE_MAP:
        if app in text:
            apps_found.append(app)

    if len(apps_found) >= 2:
        # Try to find an article that covers both
        for app in apps_found:
            link = ARTICLE_MAP.get(app)
            if link:
                return apps_found[0], apps_found[1], link
    elif len(apps_found) == 1:
        return apps_found[0], "competitors", ARTICLE_MAP.get(apps_found[0], SITE_URL)

    return "Shopify app", "alternative", SITE_URL


def generate_reply(title: str, body: str, client: OpenAI | None) -> str:
    app_a, app_b, article_link = _detect_topic(title, body)

    if not client or not DEEPSEEK_API_KEY:
        # Fallback manual reply
        return (
            f"I've worked with both {app_a.title()} and {app_b.title()} on high-volume Shopify stores. "
            f"The main technical difference comes down to API latency and webhook reliability. "
            f"We ran controlled benchmarks on identical infrastructure if you want the raw numbers: {article_link}"
        )

    sys_msg = (
        "You are a senior Shopify solutions architect. "
        "Write a helpful, technical Reddit reply (max 120 words). "
        "Rules:\n"
        "1. Lead with specific technical insight (API latency, DOM bloat, webhook throughput, cache hit ratio).\n"
        "2. Do NOT use marketing language like 'best', '#1', 'amazing', 'game-changer'.\n"
        "3. Do NOT include the link in the first 2 sentences.\n"
        "4. End with ONE casual sentence referencing your benchmark data and the link.\n"
        "5. Sound like a senior engineer on StackOverflow, not a marketer."
    )

    user_msg = (
        f"Reddit post title: {title}\n"
        f"Post body: {body[:500]}\n"
        f"Apps discussed: {app_a} vs {app_b}\n"
        f"Your benchmark article: {article_link}\n\n"
        f"Write the reply."
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.6,
            max_tokens=250,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] LLM failed: {e}")
        return (
            f"From a technical standpoint, {app_a.title()} and {app_b.title()} differ significantly in API latency and webhook architecture. "
            f"We benchmarked both on identical infrastructure; the raw JSON payloads and latency percentiles are here: {article_link}"
        )


# ============================================================
# Main
# ============================================================
def run_once(client: OpenAI | None):
    print("=" * 70)
    print(f"ToolCompareLabs Reddit Monitor — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    all_hits = []
    for sub in SUBREDDITS:
        posts = fetch_posts(sub, limit=25)
        hits = filter_posts(posts, KEYWORDS)
        print(f"r/{sub}: scanned {len(posts)} posts, {len(hits)} keyword hits")
        all_hits.extend(hits)

    if not all_hits:
        print("\nNo matching posts found. Try again later.")
        return

    print(f"\n{'='*70}")
    print(f"FOUND {len(all_hits)} MATCHING POST(S)")
    print(f"{'='*70}\n")

    for idx, post in enumerate(all_hits, 1):
        title = post.get("title", "")
        permalink = f"https://reddit.com{post.get('permalink', '')}"
        selftext = post.get("selftext", "")
        author = post.get("author", "unknown")
        created_utc = post.get("created_utc", 0)
        age_min = int((datetime.now(timezone.utc).timestamp() - created_utc) / 60)

        print(f"[{idx}] r/{post.get('subreddit')} — {age_min}m ago — u/{author}")
        print(f"    Title: {title}")
        print(f"    Link:  {permalink}")
        print()

        reply = generate_reply(title, selftext, client)
        print("-" * 70)
        print("SUGGESTED REPLY:")
        print("-" * 70)
        print(reply)
        print("-" * 70)
        print()


def run_watch(client: OpenAI | None, interval_sec: int = 300):
    seen_ids = set()
    print(f"Watching r/shopify + r/ecommerce every {interval_sec}s. Press Ctrl+C to stop.\n")

    while True:
        try:
            for sub in SUBREDDITS:
                posts = fetch_posts(sub, limit=25)
                hits = filter_posts(posts, KEYWORDS)
                new_hits = [p for p in hits if p.get("id") not in seen_ids]

                for post in new_hits:
                    seen_ids.add(post.get("id"))
                    title = post.get("title", "")
                    permalink = f"https://reddit.com{post.get('permalink', '')}"
                    selftext = post.get("selftext", "")

                    print(f"\n[NEW HIT] r/{sub} — {title}")
                    print(f"Link: {permalink}")
                    reply = generate_reply(title, selftext, client)
                    print(f"\nSUGGESTED REPLY:\n{reply}\n{'='*70}")

            time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


def run_test(title: str, client: OpenAI | None):
    print(f"Test prompt: {title}\n")
    reply = generate_reply(title, "", client)
    print(reply)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToolCompareLabs Reddit Monitor")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--watch", action="store_true", help="Loop every 5 minutes")
    parser.add_argument("--test", type=str, help="Test with a custom post title")
    parser.add_argument("--interval", type=int, default=300, help="Watch interval in seconds (default: 300)")
    args = parser.parse_args()

    client = None
    if DEEPSEEK_API_KEY:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
    else:
        print("[WARN] DEEPSEEK_API_KEY not set. Fallback replies will be used.")

    if args.test:
        run_test(args.test, client)
    elif args.watch:
        run_watch(client, interval_sec=args.interval)
    else:
        run_once(client)
