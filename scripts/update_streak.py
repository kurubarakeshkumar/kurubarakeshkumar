#!/usr/bin/env python3
"""
Daily GitHub Streak Updater
Runs inside GitHub Actions every day at 11:45 PM IST.
Updates streak.json, history.csv, and patches the README streak badge.
"""

import json
import os
import csv
import requests
from datetime import datetime, timedelta
import pytz

# ── Config ──────────────────────────────────────────────────────────────────
USERNAME   = os.environ.get("GITHUB_USERNAME", "kurubarakeshkumar")
TOKEN      = os.environ.get("GITHUB_TOKEN", "")
IST        = pytz.timezone("Asia/Kolkata")
TODAY      = datetime.now(IST).strftime("%Y-%m-%d")
STREAK_FILE   = "streak/streak.json"
HISTORY_FILE  = "streak/history.csv"
README_FILE   = "README.md"

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def load_streak():
    if os.path.exists(STREAK_FILE):
        with open(STREAK_FILE) as f:
            return json.load(f)
    return {
        "username": USERNAME,
        "current_streak": 0,
        "longest_streak": 0,
        "last_activity_date": None,
        "total_days_active": 0,
        "streak_start_date": TODAY,
        "history": []
    }

def save_streak(data):
    os.makedirs("streak", exist_ok=True)
    with open(STREAK_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ streak.json saved — Current streak: {data['current_streak']} days")

def append_history(date, committed, commit_type):
    os.makedirs("streak", exist_ok=True)
    file_exists = os.path.exists(HISTORY_FILE)
    rows = []
    if file_exists:
        with open(HISTORY_FILE, newline="") as f:
            rows = list(csv.DictReader(f))
    # Keep only last 30 days
    rows = [r for r in rows if r["date"] != date][-29:]
    rows.append({"date": date, "committed": str(committed), "type": commit_type})
    with open(HISTORY_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "committed", "type"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ history.csv updated ({len(rows)} entries)")

def check_manual_activity():
    """Check if the user already committed manually today (IST)."""
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        events = resp.json() if resp.ok else []
        for event in events:
            if event.get("type") == "PushEvent":
                created = event.get("created_at", "")[:10]
                if created == TODAY:
                    return True
    except Exception as e:
        print(f"⚠️  Could not check events: {e}")
    return False

def update_readme(streak_data):
    """Patch the streak stats table in README.md."""
    if not os.path.exists(README_FILE):
        return
    with open(README_FILE) as f:
        content = f.read()

    streak_block = f"""<!-- STREAK_START -->
## 🔥 Streak Stats

| 🔥 Current Streak | 🏆 Longest Streak | 📅 Streak Since | ✅ Total Days Active |
|:---:|:---:|:---:|:---:|
| **{streak_data['current_streak']} days** | **{streak_data['longest_streak']} days** | {streak_data['streak_start_date']} | {streak_data['total_days_active']} days |

> 🤖 Auto-updated daily at 11:45 PM IST &nbsp;•&nbsp; Last check-in: `{TODAY}`
<!-- STREAK_END -->"""

    if "<!-- STREAK_START -->" in content and "<!-- STREAK_END -->" in content:
        import re
        content = re.sub(
            r"<!-- STREAK_START -->.*?<!-- STREAK_END -->",
            streak_block,
            content,
            flags=re.DOTALL
        )
    else:
        # Append before the footer wave
        content = content.replace(
            "---\n\n<div align=\"center\">\n\n### 🤝 Let's Connect",
            f"---\n\n{streak_block}\n\n---\n\n<div align=\"center\">\n\n### 🤝 Let's Connect"
        )

    with open(README_FILE, "w") as f:
        f.write(content)
    print("✅ README.md streak section updated")

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"🗓️  Running streak updater for {TODAY} (IST)")
    data = load_streak()

    last = data.get("last_activity_date")
    yesterday = (datetime.now(IST) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Determine commit type
    had_manual = check_manual_activity()
    commit_type = "manual" if had_manual else "auto"
    print(f"📋 Manual activity today: {had_manual}")

    # Update streak logic
    if last == TODAY:
        print("ℹ️  Already recorded today. Skipping streak increment.")
    elif last == yesterday or last is None:
        # Continuing streak
        data["current_streak"] += 1
        data["total_days_active"] += 1
        data["last_activity_date"] = TODAY
        if data["current_streak"] > data["longest_streak"]:
            data["longest_streak"] = data["current_streak"]
        print(f"🔥 Streak extended to {data['current_streak']} days!")
    else:
        # Streak broken — reset
        print(f"💔 Streak broken! Last activity was {last}. Resetting.")
        data["current_streak"] = 1
        data["total_days_active"] += 1
        data["last_activity_date"] = TODAY
        data["streak_start_date"] = TODAY

    # Save everything
    save_streak(data)
    append_history(TODAY, True, commit_type)
    update_readme(data)
    print("🚀 All done!")

if __name__ == "__main__":
    main()
