#!/usr/bin/env python3
"""
gh-bounty-scout — GitHub Bounty Scanner CLI
Scanează issue-uri cu recompensă și le afișează frumos în terminal.
Zero dependințe externe (doar Python stdlib).

Folosire:
  gh-bounty-scout.py scan
  gh-bounty-scout.py scan --all
  gh-bounty-scout.py watch
  gh-bounty-scout.py stats
  gh-bounty-scout.py clear-cache
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# ─── Constants ───────────────────────────────────────────────────────────────

CACHE_DIR = os.path.expanduser("~/.gh-bounty-scout")
CACHE_FILE = os.path.join(CACHE_DIR, "seen.json")
STATS_FILE = os.path.join(CACHE_DIR, "stats.json")
GITHUB_API = "https://api.github.com"
VERSION = "1.0.0"

COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_CYAN = "\033[96m"
COLOR_GRAY = "\033[90m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"

# ─── GitHub API ──────────────────────────────────────────────────────────────

QUERIES = [
    'label:bounty+state:open+is:issue',
    'label:"Price:"+state:open+is:issue',
    'bounty+in:title+state:open+is:issue',
    'label:reward+state:open+is:issue',
]

BOUNTY_PATTERNS = [
    (r'\$(\d+(?:\.\d+)?)\s*(?:USD|usd)?', 1),
    (r'Price:\s*\$?(\d+(?:\.\d+)?)\s*USD', 1),
    (r'Price:\s*(\d+(?:\.\d+)?)\s*USD', 1),
    (r'bounty[:\s]*\$?(\d+(?:\.\d+)?)', 1),
    (r'reward[:\s]*\$?(\d+(?:\.\d+)?)', 1),
    (r'(\d+(?:\.\d+)?)\s*USDC', 1),
    (r'(\d+(?:\.\d+)?)\s*USDT', 1),
    (r'prize[:\s]*\$?(\d+(?:\.\d+)?)', 1),
    (r'\$(\d+(?:\.\d+)?)', 1),
]


def github_request(path, token=None):
    """Make a GitHub API request with auth if available."""
    url = f"{GITHUB_API}/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "gh-bounty-scout/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            remaining = int(r.headers.get("X-RateLimit-Remaining", 0))
            reset_at = int(r.headers.get("X-RateLimit-Reset", 0))
            return data, remaining, reset_at
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": str(e), "status": e.code, "body": body}, 0, 0
    except Exception as e:
        return {"error": str(e)}, 0, 0


def extract_bounty(title, body, labels):
    """Extract bounty amount from title, body, and labels."""
    combined = f"{title} {body[:2000]}"
    for label in labels:
        combined += f" {label.get('name', '')}"
    
    best = 0
    for pattern, group in BOUNTY_PATTERNS:
        matches = re.findall(pattern, combined, re.IGNORECASE)
        for m in matches:
            try:
                val = float(m) if isinstance(m, str) else float(m[0]) if isinstance(m, tuple) else 0
                if 1 <= val <= 10000 and val > best:
                    best = val
            except (ValueError, IndexError):
                pass
    return best


def scan_bounties(token=None, max_pages=3):
    """Scan GitHub for bounty issues."""
    all_items = []
    rate_remaining = None
    
    for query in QUERIES:
        for page in range(1, max_pages + 1):
            path = f"search/issues?q={urllib.parse.quote(query)}&sort=updated&per_page=20&page={page}"
            data, remaining, reset_at = github_request(path, token)
            
            if rate_remaining is None:
                rate_remaining = remaining
            else:
                rate_remaining = min(rate_remaining, remaining)
            
            if "error" in data:
                break
            
            for item in data.get("items", []):
                if item.get("state") != "open":
                    continue
                
                title = item.get("title", "")
                body = (item.get("body") or "")
                repo_url = item.get("repository_url") or ""
                if "/repos/" in repo_url:
                    repo_name = repo_url.split("/repos/")[-1]
                else:
                    html = item.get("html_url") or ""
                    parts = html.split("/")
                    repo_name = "/".join(parts[3:5]) if len(parts) >= 5 else "unknown"
                
                labels = item.get("labels", [])
                bounty = extract_bounty(title, body, labels)
                
                all_items.append({
                    "title": title.strip()[:120],
                    "repo": repo_name,
                    "bounty": bounty,
                    "url": item.get("html_url", ""),
                    "labels": [l.get("name", "") for l in labels],
                    "updated": item.get("updated_at", ""),
                    "created": item.get("created_at", ""),
                })
            
            if page < max_pages:
                time.sleep(0.3)
        
        time.sleep(0.5)
    
    return all_items, rate_remaining


# ─── Cache ───────────────────────────────────────────────────────────────────

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_seen():
    ensure_cache_dir()
    try:
        with open(CACHE_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    ensure_cache_dir()
    with open(CACHE_FILE, "w") as f:
        json.dump(list(seen), f)


def load_stats():
    ensure_cache_dir()
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_scans": 0, "total_bounties_found": 0, "total_value_found": 0.0, "last_scan": None}


def save_stats(stats):
    ensure_cache_dir()
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def clear_cache():
    ensure_cache_dir()
    for f in [CACHE_FILE, STATS_FILE]:
        if os.path.exists(f):
            os.remove(f)
    return "Cache-ul a fost golit."


# ─── Display ─────────────────────────────────────────────────────────────────

def color_by_bounty(amount):
    if amount >= 50:
        return COLOR_GREEN
    elif amount >= 20:
        return COLOR_YELLOW
    elif amount > 0:
        return COLOR_CYAN
    return COLOR_GRAY


def fmt_time(iso_str):
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        if diff.days > 30:
            return f"{diff.days // 30}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "now"
    except (ValueError, TypeError):
        return iso_str[:10] if iso_str else "?"


def print_bounty(b, index=0, show_labels=False):
    """Print a single bounty line."""
    bounty_str = f"${b['bounty']:.0f}" if b['bounty'] > 0 else "   -"
    color = color_by_bounty(b['bounty'])
    
    title = b['title'][:60].ljust(62)
    repo = b['repo'][:30].ljust(32)
    updated = fmt_time(b['updated']).rjust(8)
    
    line = f" {str(index+1).rjust(2)}  {color}{bounty_str}{COLOR_RESET}  {COLOR_BOLD}{title}{COLOR_RESET}  {COLOR_CYAN}{repo}{COLOR_RESET}  {COLOR_GRAY}{updated}{COLOR_RESET}"
    print(line)
    
    if show_labels and b['labels']:
        labels_str = ", ".join(b['labels'][:5])
        print(f"     {COLOR_GRAY}labels: {labels_str}{COLOR_RESET}")
    
    print(f"     {COLOR_GRAY}{b['url']}{COLOR_RESET}")


def print_table(bounties, title="Bounties", show_labels=False):
    """Print a formatted table of bounties."""
    if not bounties:
        print(f"{COLOR_GRAY}Niciun bounty găsit.{COLOR_RESET}")
        return
    
    print(f"\n{COLOR_BOLD}{COLOR_MAGENTA}═══ {title} ═══{COLOR_RESET}\n")
    print(f" {COLOR_BOLD}   {'$':>5}  {'TITLE':<62}  {'REPO':<32}  {'AGE':>8}{COLOR_RESET}")
    print(f" {COLOR_GRAY}{'─'*5}  {'─'*62}  {'─'*32}  {'─'*8}{COLOR_RESET}")
    
    for i, b in enumerate(bounties):
        print_bounty(b, i, show_labels)
        if i < len(bounties) - 1:
            print(f" {COLOR_GRAY}{'─'*5}  {'─'*62}  {'─'*32}  {'─'*8}{COLOR_RESET}")
    
    # Summary
    total_value = sum(b['bounty'] for b in bounties)
    with_bounty = sum(1 for b in bounties if b['bounty'] > 0)
    print(f"\n {COLOR_GRAY}Total: {len(bounties)} bounties, {with_bounty} cu $ (${total_value:.0f} sum){COLOR_RESET}")


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_scan(args):
    """Scan GitHub and display new bounties."""
    token = os.environ.get("GITHUB_TOKEN") or args.token
    
    print(f"{COLOR_GRAY}Scanning GitHub for bounties...{COLOR_RESET}")
    all_bounties, remaining = scan_bounties(token, args.pages)
    
    if not all_bounties:
        print(f"{COLOR_RED}Eroare la scanare sau 0 rezultate. Rate remaining: {remaining}{COLOR_RESET}")
        return
    
    seen = load_seen() if not args.all else set()
    
    new_bounties = [b for b in all_bounties if b["url"] not in seen]
    stats = load_stats()
    
    # Update seen
    if not args.all:
        for b in all_bounties:
            seen.add(b["url"])
        save_seen(seen)
    
    # Update stats
    stats["total_scans"] += 1
    new_value = sum(b["bounty"] for b in new_bounties)
    stats["total_bounties_found"] += len(new_bounties)
    stats["total_value_found"] += new_value
    stats["last_scan"] = datetime.now().isoformat()
    save_stats(stats)
    
    # Display
    if new_bounties and not args.all:
        new_bounties.sort(key=lambda x: x["bounty"], reverse=True)
        print_table(new_bounties, f"NOU: {len(new_bounties)} bounties", args.labels)
        
        with_bounty = [b for b in new_bounties if b['bounty'] > 0]
        if with_bounty:
            print(f"\n{COLOR_GREEN}{COLOR_BOLD}Bounties cu bani (target):{COLOR_RESET}")
            for b in with_bounty:
                print(f"  {color_by_bounty(b['bounty'])}${b['bounty']:.0f}{COLOR_RESET} {b['title'][:50]} → {COLOR_CYAN}{b['url']}{COLOR_RESET}")
    elif args.all:
        all_bounties.sort(key=lambda x: x["bounty"], reverse=True)
        print_table(all_bounties, f"TOATE: {len(all_bounties)} bounties", args.labels)
    else:
        print(f"{COLOR_GRAY}Nimic nou. Ultimele {len(all_bounties)} bounties sunt deja în cache.{COLOR_RESET}")
    
    # Rate limit warning
    if remaining is not None and remaining < 10:
        print(f"\n{COLOR_RED}⚠ API rate limit scăzut: {remaining} remaining.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}  Setează GITHUB_TOKEN pentru 5000 req/h.{COLOR_RESET}")
    elif remaining is not None:
        print(f"\n{COLOR_GRAY}API rate limit: {remaining} remaining{COLOR_RESET}")


def cmd_watch(args):
    """Watch mode — scan every 60s."""
    token = os.environ.get("GITHUB_TOKEN") or args.token
    interval = args.interval
    
    print(f"{COLOR_BOLD}{COLOR_GREEN}Watch mode activ. Scanez la fiecare {interval}s.{COLOR_RESET}")
    print(f"{COLOR_GRAY}Ctrl+C pentru a opri.{COLOR_RESET}\n")
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"{COLOR_CYAN}[{now}]{COLOR_RESET} Scanning...", end=" ", flush=True)
            
            all_bounties, remaining = scan_bounties(token, 2)
            seen = load_seen()
            
            new_bounties = [b for b in all_bounties if b["url"] not in seen]
            
            if new_bounties:
                print(f"{COLOR_GREEN}found {len(new_bounties)} new!{COLOR_RESET}")
                for b in new_bounties:
                    seen.add(b["url"])
                    bounty_str = f"${b['bounty']:.0f}" if b['bounty'] > 0 else "no $"
                    print(f"  {color_by_bounty(b['bounty'])}{bounty_str}{COLOR_RESET} {b['title'][:50]}")
                    print(f"  {COLOR_GRAY}{b['url']}{COLOR_RESET}")
                save_seen(seen)
                print()
            else:
                print(f"{COLOR_GRAY}nothing new (rate: {remaining}){COLOR_RESET}")
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{COLOR_GRAY}Watch mode oprit.{COLOR_RESET}")


def cmd_stats(args):
    """Show scan statistics."""
    stats = load_stats()
    
    print(f"\n{COLOR_BOLD}{COLOR_MAGENTA}═══ Stats ═══{COLOR_RESET}\n")
    print(f"  Scanuri totale:     {stats['total_scans']}")
    print(f"  Bounties găsite:    {stats['total_bounties_found']}")
    print(f"  Valoare totală:     ${stats['total_value_found']:.2f}")
    print(f"  Ultimul scan:       {stats['last_scan'] or 'niciodată'}")
    
    seen_count = len(load_seen())
    print(f"  În cache:           {seen_count} issue-uri")
    
    # Average
    if stats['total_scans'] > 0:
        avg = stats['total_bounties_found'] / stats['total_scans']
        print(f"  Medie/scan:         {avg:.1f} bounties")
    print()


def cmd_clear(args):
    """Clear cache."""
    msg = clear_cache()
    print(f"{COLOR_GREEN}{msg}{COLOR_RESET}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="gh-bounty-scout — GitHub Bounty Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:
  gh-bounty-scout.py scan              # Scanează și arată bounties noi
  gh-bounty-scout.py scan --all        # Arată toate bounties (inclusiv văzute)
  gh-bounty-scout.py scan --labels     # Arată și etichetele
  gh-bounty-scout.py watch             # Watch mode (la fiecare 60s)
  gh-bounty-scout.py watch --interval 30  # Watch la 30s
  gh-bounty-scout.py stats             # Statistici
  gh-bounty-scout.py clear-cache       # Gol cache
        """
    )
    parser.add_argument("--token", help="GitHub token (sau GITHUB_TOKEN env)")
    
    sub = parser.add_subparsers(dest="command", required=True)
    
    # scan
    p_scan = sub.add_parser("scan", help="Scanează GitHub pentru bounties")
    p_scan.add_argument("--all", action="store_true", help="Arată toate, nu doar noi")
    p_scan.add_argument("--labels", action="store_true", help="Arată etichetele")
    p_scan.add_argument("--pages", type=int, default=2, help="Pagini de căutat (def: 2)")
    
    # watch
    p_watch = sub.add_parser("watch", help="Watch mode — scan periodic")
    p_watch.add_argument("--interval", type=int, default=60, help="Secunde între scanări (def: 60)")
    
    # stats
    sub.add_parser("stats", help="Arată statistici")
    
    # clear-cache
    sub.add_parser("clear-cache", help="Golește cache-ul")
    
    args = parser.parse_args()
    
    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "clear-cache":
        cmd_clear(args)


if __name__ == "__main__":
    main()
