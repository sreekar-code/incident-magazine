$ cat /Users/sreekar/Documents/Dev/slack-incident-magazine/magazine.py

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
    """Fetch top relevant HN stories from the past 30 days via Algolia."""
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

def fetch_reddit_posts(n=2):
    """Fetch hot posts from r/devops and r/sre and filter locally."""
    subreddits = ["devops", "sre"]
    headers = {"User-Agent": "SlackIncidentMagazine/1.0 (daily digest bot)"}
    candidates = []

    for sub in subreddits:
        # Fetch hot posts and top posts from the week
        for sort in ["hot", "top"]:
            params = "?limit=25" if sort == "hot" else "?limit=25&t=week"
            url = f"https://www.reddit.com/r/{sub}/{sort}.json{params}"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                children = resp.json().get("data", {}).get("children", [])
                for child in children:
                    post = child["data"]
                    if is_relevant(post.get("title", "") + " " + post.get("selftext", "")):
                        candidates.append(post)
            except Exception as e:
                print(f"Reddit fetch error for r/{sub}/{sort}: {e}")

    # Deduplicate by post id, then rank by score
    seen = {}
    for post in candidates:
        pid = post["id"]
        if pid not in seen:
            seen[pid] = post

    ranked = sorted(seen.values(), key=lambda p: p.get("score", 0), reverse=True)
    return ranked[:n]

def build_digest(hn_posts, reddit_posts):
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
                    "text": "Top stories on incident response, on-call, and reliability from Hacker News & Reddit.",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🔶  Hacker News*"},
        },
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
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No relevant HN stories found today._"},
        })

    blocks += [
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🤖  Reddit — r/devops & r/sre*"},
        },
    ]

    if reddit_posts:
        for post in reddit_posts:
            title = post.get("title", "Untitled")
            permalink = f"https://reddit.com{post.get('permalink', '')}"
            score = post.get("score", 0)
            comments = post.get("num_comments", 0)
            subreddit = post.get("subreddit_name_prefixed", "r/?")
            author = post.get("author", "")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{permalink}|{title}>*\n"
                        f"↑ {score}  ·  {subreddit}  ·  u/{author}  ·  {comments} comments"
                    ),
                },
            })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No relevant Reddit posts found today._"},
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Delivered daily at 9 AM IST  ·  Sources: Hacker News, r/devops, r/sre"}],
    })

    return {"blocks": blocks}

def post_to_slack(payload):
    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

if __name__ == "__main__":
    print("Fetching HN posts...")
    hn = fetch_hn_posts()
    print(f"  Found {len(hn)} HN posts")

    print("Fetching Reddit posts...")
    reddit = fetch_reddit_posts()
    print(f"  Found {len(reddit)} Reddit posts")

    digest = build_digest(hn, reddit)

    print("Posting to Slack...")
    post_to_slack(digest)
    print("Done!")
