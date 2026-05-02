# Incident Management Daily

A daily Slack digest of the best articles and discussions on incident management, on-call engineering, and site reliability — delivered every morning at 9 AM IST.

## What it does

Every day at 9 AM IST, a GitHub Actions workflow runs and posts a digest to your Slack channel with:

- **2 posts from Hacker News** — top stories matching incident/on-call/reliability keywords from the past 30 days
- **2 posts from DEV.to** — top articles tagged `devops`, `sre`, or `incident` from the past 30 days

Posts are deduplicated — once a story is sent, it won't appear again.

## Sources

| Source | How it's fetched |
|---|---|
| Hacker News | Algolia HN Search API, filtered by keyword, ranked by points |
| DEV.to | Public articles API, filtered by tag + keyword, ranked by reactions |

## Setup

### 1. Slack Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch
2. Enable **Incoming Webhooks**
3. Add webhook to your workspace and pick a channel
4. Copy the webhook URL

### 2. GitHub Secret

In your repo → Settings → Secrets and variables → Actions → New repository secret:

- Name: `SLACK_WEBHOOK_URL`
- Value: your webhook URL from above

### 3. Permissions

The workflow needs write access to commit `seen_posts.json` back to the repo. This is handled via `permissions: contents: write` in the workflow file — no extra setup needed.

## Running manually

Go to Actions → Daily Incident Magazine → Run workflow.

## Files

```
magazine.py                        # Main script
requirements.txt                   # Python dependencies
seen_posts.json                    # Auto-generated, tracks sent post IDs
.github/workflows/daily-magazine.yml  # GitHub Actions workflow
```

## Schedule

Runs daily at `30 3 * * *` UTC (9:00 AM IST).
