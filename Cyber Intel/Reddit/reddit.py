import requests
import time
import sys
import json
import csv
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIG – Realistic browser headers (use old.reddit.com)
# ----------------------------------------------------------------------
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
BASE_URL = "https://old.reddit.com"
DELAY = 2  # seconds between requests

# ----------------------------------------------------------------------
# Session creator (warms up with cookies)
# ----------------------------------------------------------------------
def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(BASE_URL, timeout=10)
    except:
        pass
    time.sleep(DELAY)
    return s

# ----------------------------------------------------------------------
# 1. Fetch posts from a subreddit
# ----------------------------------------------------------------------
def get_posts(session, subreddit, listing="hot", limit=10, time_filter="day"):
    posts = []
    after = None
    url_base = f"{BASE_URL}/r/{subreddit}/{listing}.json"
    params = {"limit": 100, "t": time_filter}

    while len(posts) < limit:
        if after:
            params["after"] = after
        try:
            resp = session.get(url_base, params=params, timeout=10)
            if resp.status_code == 403:
                print("  [!] HTTP 403 – blocked. Try again later or use a VPN.")
                break
            if resp.status_code != 200:
                print(f"  [!] HTTP {resp.status_code} for r/{subreddit}/{listing}")
                break
            data = resp.json()
        except Exception as e:
            print(f"  [!] Request failed: {e}")
            break

        children = data["data"]["children"]
        if not children:
            break

        for child in children:
            p = child["data"]
            posts.append({
                "id": p["id"],
                "title": p.get("title", ""),
                "author": p.get("author", "[deleted]"),
                "score": p.get("score", 0),
                "created_utc": p.get("created_utc", 0),
                "url": p.get("url", ""),
                "permalink": f"https://old.reddit.com{p.get('permalink', '')}",
                "num_comments": p.get("num_comments", 0),
                "selftext": p.get("selftext", ""),
            })
            if len(posts) >= limit:
                break

        after = data["data"]["after"]
        if not after:
            break
        time.sleep(DELAY)

    return posts[:limit]

# ----------------------------------------------------------------------
# 2. Fetch comments for a post
# ----------------------------------------------------------------------
def get_comments(session, subreddit, post_id, limit=20):
    url = f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json"
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 403:
            print("    [!] Comments 403 – blocked.")
            return []
        if resp.status_code != 200:
            print(f"    [!] Comments HTTP {resp.status_code} for post {post_id}")
            return []
        data = resp.json()
    except Exception as e:
        print(f"    [!] Comments request failed: {e}")
        return []

    if len(data) < 2:
        return []

    comments = []
    def extract(comment_listing):
        nonlocal comments
        for child in comment_listing["data"]["children"]:
            if "body" in child["data"]:
                c = child["data"]
                comments.append({
                    "body": c.get("body", ""),
                    "author": c.get("author", "[deleted]"),
                    "score": c.get("score", 0),
                    "created_utc": c.get("created_utc", 0),
                    "depth": c.get("depth", 0),
                    "permalink": f"https://old.reddit.com{c.get('permalink', '')}",
                })
            if child["data"].get("replies") and isinstance(child["data"]["replies"], dict):
                extract(child["data"]["replies"])
            if len(comments) >= limit:
                return

    extract(data[1])
    return comments[:limit]

# ----------------------------------------------------------------------
# 3. Search posts by keyword in a subreddit
# ----------------------------------------------------------------------
def search_posts(session, subreddit, query, limit=25, sort="relevance"):
    posts = []
    after = None
    url = f"{BASE_URL}/r/{subreddit}/search.json"
    params = {
        "q": query,
        "restrict_sr": "on",
        "sort": sort,
        "limit": 100
    }

    while len(posts) < limit:
        if after:
            params["after"] = after
        try:
            resp = session.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"  [!] Search HTTP {resp.status_code}")
                break
            data = resp.json()
        except Exception as e:
            print(f"  [!] Search failed: {e}")
            break

        children = data["data"]["children"]
        if not children:
            break

        for child in children:
            p = child["data"]
            posts.append({
                "id": p["id"],
                "title": p.get("title", ""),
                "author": p.get("author", "[deleted]"),
                "score": p.get("score", 0),
                "created_utc": p.get("created_utc", 0),
                "url": p.get("url", ""),
                "permalink": f"https://old.reddit.com{p.get('permalink', '')}",
                "num_comments": p.get("num_comments", 0),
                "selftext": p.get("selftext", ""),
            })
            if len(posts) >= limit:
                break

        after = data["data"]["after"]
        if not after:
            break
        time.sleep(DELAY)

    return posts[:limit]

# ----------------------------------------------------------------------
# 4. User profile: fetch recent posts & comments
# ----------------------------------------------------------------------
def get_user_activity(session, username, limit_items=20):
    posts = []
    comments = []
    after = None
    url = f"{BASE_URL}/user/{username}/overview.json"
    params = {"limit": 100}

    while (len(posts) + len(comments)) < limit_items:
        if after:
            params["after"] = after
        try:
            resp = session.get(url, params=params, timeout=10)
            if resp.status_code == 404:
                print(f"  [!] User u/{username} not found.")
                break
            if resp.status_code != 200:
                print(f"  [!] User request HTTP {resp.status_code}")
                break
            data = resp.json()
        except Exception as e:
            print(f"  [!] User request failed: {e}")
            break

        children = data["data"]["children"]
        if not children:
            break

        for child in children:
            item = child["data"]
            # Distinguish posts (selftext key) vs comments (body key)
            if "selftext" in item:   # It's a post
                posts.append({
                    "id": item["id"],
                    "title": item.get("title", ""),
                    "author": username,                     # <-- FIX: add author
                    "selftext": item.get("selftext", ""),
                    "subreddit": item.get("subreddit", ""),
                    "score": item.get("score", 0),
                    "created_utc": item.get("created_utc", 0),
                    "permalink": f"https://old.reddit.com{item.get('permalink', '')}",
                    "num_comments": item.get("num_comments", 0),
                })
            elif "body" in item:     # It's a comment
                comments.append({
                    "id": item["id"],
                    "body": item.get("body", ""),
                    "author": item.get("author", username),
                    "subreddit": item.get("subreddit", ""),
                    "score": item.get("score", 0),
                    "created_utc": item.get("created_utc", 0),
                    "permalink": f"https://old.reddit.com{item.get('permalink', '')}",
                })
            if len(posts) + len(comments) >= limit_items:
                break

        after = data["data"]["after"]
        if not after:
            break
        time.sleep(DELAY)

    return {"posts": posts[:limit_items], "comments": comments[:limit_items]}

# ----------------------------------------------------------------------
# 5. Trend analysis: top posts across multiple time windows
# ----------------------------------------------------------------------
def trend_analysis(session, subreddit, limit=5):
    time_filters = ["hour", "day", "week", "month", "year", "all"]
    results = {}
    print(f"  Fetching top {limit} posts for each time window...")
    for tf in time_filters:
        print(f"    - past {tf} ...")
        posts = get_posts(session, subreddit, listing="top", limit=limit, time_filter=tf)
        results[tf] = posts
    return results

# ----------------------------------------------------------------------
# File saving utilities
# ----------------------------------------------------------------------
def save_to_file(data, base_filename="reddit_osint"):
    print("\nSave results to file? (y/n): ", end="")
    if input().strip().lower() != 'y':
        return

    print("Choose format: [json / txt / csv]: ", end="")
    fmt = input().strip().lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        filename = f"{base_filename}_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved as {filename}")

    elif fmt == "txt":
        filename = f"{base_filename}_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            if isinstance(data, list):
                for idx, post in enumerate(data, 1):
                    f.write(f"--- Post {idx} ---\n")
                    f.write(f"Title: {post.get('title','')}\n")
                    f.write(f"Author: {post.get('author','')}\n")
                    f.write(f"Score: {post.get('score','')}\n")
                    f.write(f"URL: {post.get('permalink','')}\n")
                    f.write(f"Text: {post.get('selftext','')}\n\n")
            elif isinstance(data, dict):
                json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved as {filename}")

    elif fmt == "csv":
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            filename = f"{base_filename}_{timestamp}.csv"
            keys = data[0].keys()
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            print(f"  Saved as {filename}")
        else:
            print("  CSV format is only available for a simple list of posts (current data not suitable).")
    else:
        print("  Invalid format – no file saved.")

# ----------------------------------------------------------------------
# Display helpers (now safe even if keys are missing)
# ----------------------------------------------------------------------
def display_posts(posts):
    for i, p in enumerate(posts, 1):
        title = p.get("title", "[no title]")
        author = p.get("author", "unknown")
        score = p.get("score", 0)
        comments = p.get("num_comments", "?")
        selftext = p.get("selftext", "")
        permalink = p.get("permalink", "")

        print(f"\n  [{i}/{len(posts)}] {title}")
        print(f"      Author: u/{author} | Score: {score} | Comments: {comments}")
        if selftext:
            text = selftext.replace('\n', ' ')[:200]
            print(f"      Text: {text}...")
        print(f"      URL: {permalink}")

def display_comments(comments, limit=5):
    for c in comments[:limit]:
        author = c.get("author", "unknown")
        score = c.get("score", 0)
        depth = c.get("depth", 0)
        body = c.get("body", "").replace('\n', ' ')[:150]
        indent = "  " * (depth + 1)
        print(f"{indent}- u/{author} ({score}pts): {body}")

# ----------------------------------------------------------------------
# Menu & main interaction
# ----------------------------------------------------------------------
def main_menu(session):
    while True:
        print("\n" + "=" * 60)
        print(" REDDIT OSINT TOOL")
        print("=" * 60)
        print("1. Investigate subreddit (posts & comments)")
        print("2. Search posts by keyword")
        print("3. User profile analysis")
        print("4. Trend analysis (top posts over time)")
        print("5. Exit")
        choice = input(">> ").strip()

        if choice == "1":
            subs = input("Subreddit(s) (comma‑separated): ").strip().split(",")
            subs = [s.strip() for s in subs if s.strip()]
            if not subs:
                print("No subreddit entered.")
                continue
            listing = input("Listing (hot/new/top/rising) [hot]: ").strip().lower()
            if listing not in ("hot","new","top","rising"):
                listing = "hot"
            time_filter = "week"
            if listing == "top":
                tf = input("Time filter (hour/day/week/month/year/all) [week]: ").strip()
                if tf in ("hour","day","week","month","year","all"):
                    time_filter = tf
            try:
                max_posts = int(input("Posts per subreddit [10]: ") or 10)
            except:
                max_posts = 10
            try:
                max_comments = int(input("Comments per post [5]: ") or 5)
            except:
                max_comments = 5

            for sub in subs:
                print(f"\n--- r/{sub} ({listing}) ---")
                posts = get_posts(session, sub, listing, max_posts, time_filter)
                if not posts:
                    print("  No posts found.")
                    continue
                display_posts(posts)
                if max_comments > 0:
                    for p in posts:
                        print(f"\n    Comments for post {p['id']}:")
                        comments = get_comments(session, sub, p['id'], max_comments)
                        display_comments(comments, max_comments)
                        time.sleep(DELAY)
                print("-"*40)
                save_to_file(posts, f"reddit_osint_{sub}_{listing}")

        elif choice == "2":
            sub = input("Subreddit to search: ").strip()
            if not sub:
                print("No subreddit.")
                continue
            query = input("Keyword(s): ").strip()
            if not query:
                print("No keyword.")
                continue
            try:
                limit = int(input("How many results? [25]: ") or 25)
            except:
                limit = 25
            print(f"\nSearching r/{sub} for '{query}'...")
            results = search_posts(session, sub, query, limit)
            if not results:
                print("  Nothing found.")
            else:
                display_posts(results)
                save_to_file(results, f"search_{sub}_{query}")

        elif choice == "3":
            username = input("Reddit username (without u/): ").strip()
            if not username:
                print("No username.")
                continue
            try:
                limit = int(input("How many recent items? [20]: ") or 20)
            except:
                limit = 20
            print(f"\nFetching u/{username} ...")
            activity = get_user_activity(session, username, limit)
            if activity["posts"]:
                print(f"\n--- Latest {len(activity['posts'])} posts ---")
                display_posts(activity["posts"])
            else:
                print("  No recent posts.")
            if activity["comments"]:
                print(f"\n--- Latest {len(activity['comments'])} comments ---")
                for i, c in enumerate(activity["comments"], 1):
                    print(f"\n  [{i}] r/{c.get('subreddit','?')} | Score: {c.get('score',0)}")
                    print(f"      {c.get('body','')[:200]}")
                    print(f"      URL: {c.get('permalink','')}")
            else:
                print("  No recent comments.")
            save_to_file(activity, f"user_{username}")

        elif choice == "4":
            sub = input("Subreddit: ").strip()
            if not sub:
                print("No subreddit.")
                continue
            try:
                limit = int(input("Posts per time window? [5]: ") or 5)
            except:
                limit = 5
            trends = trend_analysis(session, sub, limit)
            for tf, posts in trends.items():
                print(f"\n=== Top {limit} past {tf} ===")
                display_posts(posts)
            save_to_file(trends, f"trends_{sub}")

        elif choice == "5":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice, try again.")

# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print(" Warming up session (cookies)...")
    session = get_session()
    try:
        main_menu(session)
    except KeyboardInterrupt:
        print("\n\nExited by user.")
        sys.exit(0)