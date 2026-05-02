# Agents

## daily-magazine

**Type:** GitHub Actions scheduled workflow  
**File:** `.github/workflows/daily-magazine.yml`  
**Schedule:** Daily at 3:30 AM UTC (9:00 AM IST)

### What it does

Runs `magazine.py` to fetch, filter, and post a daily Slack digest of incident management content.

### Steps

1. **Checkout** — pulls the latest code including `seen_posts.json`
2. **Set up Python 3.12**
3. **Install dependencies** — `pip install -r requirements.txt`
4. **Post daily magazine** — runs `magazine.py` with `SLACK_WEBHOOK_URL` injected from secrets
5. **Save seen posts** — commits and pushes the updated `seen_posts.json` back to the repo so posts aren't repeated

### Secrets required

| Secret | Description |
|---|---|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for the target channel |

### Permissions

`contents: write` — required to commit `seen_posts.json` back to the repo after each run.

### Triggers

- Scheduled: daily at `30 3 * * *` UTC
- Manual: workflow_dispatch (run anytime from the Actions tab)

---

## magazine.py

**Type:** Python script (called by the workflow)

### Functions

| Function | Description |
|---|---|
| `load_seen()` | Reads `seen_posts.json` and returns a set of already-sent post IDs |
| `save_seen(seen)` | Writes the updated set back to `seen_posts.json`, capped at 200 entries |
| `fetch_hn_posts(seen, n=2)` | Queries Algolia HN API across 5 keywords, deduplicates, returns top `n` by points |
| `fetch_devto_posts(seen, n=2)` | Queries DEV.to API across 3 tags, filters by keyword, returns top `n` by reactions |
| `build_digest(hn_posts, devto_posts)` | Assembles a Slack Block Kit message from the fetched posts |
| `post_to_slack(payload)` | POSTs the digest to the Slack webhook URL |

### Deduplication

Post IDs are stored as `hn_{id}` and `devto_{id}` in `seen_posts.json`. On each run, fetched posts are checked against this list before being included. After a successful Slack post, new IDs are appended and saved.
