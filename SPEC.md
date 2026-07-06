Build a CLI tool called "gh-bounty-scout" that scans GitHub for issues with bounties/rewards/price labels and displays them in a nice terminal UI.

## Requirements

### Core functionality
1. Search GitHub API for issues with labels: "bounty", "prize", "reward", "Price: * USD", or dollar amounts in title
2. Display results in a colorful ASCII table with columns: TITLE | REPO | BOUNTY $ | LABELS | UPDATED
3. Cache seen issues in ~/.gh-bounty-scout/seen.json
4. Support GITHUB_TOKEN env var for authenticated API (5000 req/h vs 60 req/h)
5. Color output using ANSI codes (green for $50+, yellow for $20-49, white for rest)

### Commands
- `gh-bounty-scout scan` — scan GitHub, show new bounties
- `gh-bounty-scout scan --all` — show all bounties (including seen)
- `gh-bounty-scout watch` — watch mode (scan every 60s, show new ones)
- `gh-bounty-scout clear-cache` — clear seen cache
- `gh-bounty-scout stats` — show scan stats (total found, total value, etc)

### Output format
- Rich ASCII table with borders
- Color coded by bounty amount
- Show repo name as "owner/repo" format
- Make URLs clickable (or at least show full URL)

### Technical
- Python 3 with ONLY stdlib (no external deps)
- Single file executable (`gh-bounty-scout.py`)
- Shebang: #!/usr/bin/env python3
- Handle GitHub API rate limits gracefully (show remaining on error)
- Handle pagination (scan up to 5 pages per query)
- Search multiple label patterns
- Extract bounty amounts from:
  - Label names like "Price: 200 USD", "$50", "bounty: $100"
  - Title text containing "$XX" patterns
  - Issue body for USD/USDT/USDC amounts

Put the output file at /home/kali/workspace/gh-bounty-scout/gh-bounty-scout.py
