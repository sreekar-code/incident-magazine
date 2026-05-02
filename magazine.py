import os
import requests
from datetime import datetime, timedelta

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

KEYWORDS = [
    "incident", "on-call", "oncall", "outage", "postmortem", "post-mortem",
    "alerting", "pagerduty", "runbook", "sre", "reliability", "monitoring",
    "escalation", "incident response", "on call",
]

def is_relevant(text):
    text = text.lower()
    return any(kw in text for kw in KEYWORDS)

def fetch_hn_posts(n=2):
    since = int((datetime.utcnow() - timedelta(days=30)).timestamp())
    queries = ["incident", "on-call", "reliability", "outage", "postmortem"]
    seen = {}

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
                if oid not in seen:
                    seen[oid] = hit
        except Exception as e:
            print(f"HN fetch error for '{query}': {e}")

    ranked = sorted(seen.values(), key=lambda h: h.get("points", 0), reverse=True)
    return ranked[:n]

def fetch_devto_posts(n=2):
    tags = ["devops", "sre", "incident"]
    headers = {"User-Agent": "SlackIncidentMagazine/1.0"}
    seen = {}

    for tag in tags:
        url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page=10"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            for article in resp.json():
                aid = article["id"]
                if aid not in seen and is_relevant(article.get("title", "") + " " + article.get("description", "")):
                    seen[aid] = article
        except Exception as e:
            print(f"DEV.to fetch error for tag '{tag}': {e}")

    ranked = sorted(seen.values(), key=lambda a: a.get("public_reactions_count", 0), reverse=True)
    return ranked[:n]

def build_digest(hn_posts, devto_posts):
    today = datetime.utcnow().strftime("%B %d, %Y")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰  Incident Management Daily — {today}"},
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
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "_No relevant HN stories found today._"}})

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
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "_No relevant DEV.to articles found today._"}})

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Delivered daily at 9 AM IST  ·  Sources: Hacker News, DEV.to"}],
    })

    return {"blocks": blocks}

def post_to_slack(payload):
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

if __name__ == "__main__":
    print("Fetching HN posts...")
    hn = fetch_hn_posts()
    print(f"  Found {len(hn)} HN posts")

    print("Fetching DEV.to posts...")
    devto = fetch_devto_posts()
    print(f"  Found {len(devto)} DEV.to posts")

    digest = build_digest(hn, devto)

    print("Posting to Slack...")
    post_to_slack(digest)
    print("Done!")
