import os
import json
import requests
from datetime import datetime, timedelta

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SEEN_FILE = "seen_posts.json"
MAX_SEEN = 200

KEYWORDS = [
    "incident", "on-call", "oncall", "outage", "postmortem", "post-mortem",
    "alerting", "pagerduty", "runbook", "sre", "reliability", "monitoring",
    "escalation", "incident response", "on call",
]

def is_relevant(text):
    text = text.lower()
    return any(kw in text for kw in KEYWORDS)

def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_seen(seen):
    entries = list(seen)[-MAX_SEEN:]
    with open(SEEN_FILE, "w") as f:
        json.dump(entries, f)

def fetch_hn_posts(seen, n=2):
    since = int((datetime.utcnow() - timedelta(days=7)).timestamp())
    queries = ["incident", "on-call", "reliability", "outage", "postmortem"]
    candidates = {}

    for query in queries:
        url = (
            f"https://hn.algolia.com/api/v1/search"
            f"?query={requests.utils.quote(query)}"
            f"&tags=story"
            f"&numericFilters=created_at_i>{since}"
            f"&hitsPerPage=20"
        )
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                oid = hit["objectID"]
                sid = f"hn_{oid}"
                if sid not in seen and oid not in candidates:
                    candidates[oid] = hit
        except Exception as e:
            print(f"HN fetch error for '{query}': {e}")

    ranked = sorted(candidates.values(), key=lambda h: h.get("points", 0), reverse=True)
    return ranked[:n]

def fetch_devto_posts(seen, n=2):
    tags = ["devops", "sre", "incident"]
    headers = {"User-Agent": "SlackIncidentMagazine/1.0"}
    candidates = {}

    for tag in tags:
        url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page=10"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            for article in resp.json():
                aid = article["id"]
                sid = f"devto_{aid}"
                if sid not in seen and aid not in candidates:
                    if is_relevant(article.get("title", "") + " " + article.get("description", "")):
                        candidates[aid] = article
        except Exception as e:
            print(f"DEV.to fetch error for tag '{tag}': {e}")

    ranked = sorted(candidates.values(), key=lambda a: a.get("public_reactions_count", 0), reverse=True)
    return ranked[:n]

def build_digest(hn_posts, devto_posts):
    today = datetime.utcnow().strftime("%B %d, %Y")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰  Incident Management Weekly — {today}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Top stories on incident response, on-call, and reliability from Hacker News & DEV.to.",
                }
            ],
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "*🔶  Hacker News*"}},
    ]

    if hn_posts:
        for post in hn_posts:
            title = post.get("title", "Untitled")
            story_url = post.get("url") or f"https://news.ycombinator.com/item?id={post['objectID']}"
            discuss_url = f"https://news.ycombinator.com/item?id={post['objectID']}"
            points = post.get("points", 0)
            comments = post.get("num_comments", 0)
            author = post.get("author", "")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{story_url}|{title}>*\n"
                        f"↑ {points} points by {author}  ·  <{discuss_url}|{comments} comments>"
                    ),
                },
            })
    else:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "_No new HN stories today._"}})

    blocks += [
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": "*📝  DEV.to*"}},
    ]

    if devto_posts:
        for article in devto_posts:
            title = article.get("title", "Untitled")
            url = article.get("url", "")
            reactions = article.get("public_reactions_count", 0)
            comments = article.get("comments_count", 0)
            author = article.get("user", {}).get("name", "")
            tags = "  ".join(f"`#{t}`" for t in article.get("tag_list", [])[:3])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{url}|{title}>*\n"
                        f"❤️ {reactions}  ·  💬 {comments}  ·  by {author}  ·  {tags}"
                    ),
                },
            })
    else:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "_No new DEV.to articles today._"}})

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Delivered every Monday at 9 AM IST  ·  Sources: Hacker News, DEV.to"}],
    })

    return {"blocks": blocks}

def post_to_slack(payload):
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

if __name__ == "__main__":
    seen = load_seen()
    print(f"Loaded {len(seen)} seen post IDs")

    print("Fetching HN posts...")
    hn = fetch_hn_posts(seen)
    print(f"  Found {len(hn)} new HN posts")

    print("Fetching DEV.to posts...")
    devto = fetch_devto_posts(seen)
    print(f"  Found {len(devto)} new DEV.to posts")

    digest = build_digest(hn, devto)

    print("Posting to Slack...")
    post_to_slack(digest)
    print("Posted!")

    for post in hn:
        seen.add(f"hn_{post['objectID']}")
    for article in devto:
        seen.add(f"devto_{article['id']}")

    save_seen(seen)
    print(f"Saved {len(seen)} seen post IDs")
