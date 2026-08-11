import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import random

EXCLUDE_PATHS = {'PostList', 'PostView', 'Redirect', 'mypage', 'naver.me',
                 'neighborList', 'prologue', 'widget', ''}

class NaverBlogExtractor:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self.results = []
        self.current_query = ""
        self.session = requests.Session()
        self._warmed_up = False

    def _headers(self, referer=None):
        h = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',

            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if referer:
            h['Referer'] = referer
        return h

    def _warm_up(self):
        if self._warmed_up:
            return
        try:
            self.session.get("https://www.naver.com", headers=self._headers(), timeout=10)
            time.sleep(random.uniform(1.5, 2.5))
            self._warmed_up = True
        except Exception as e:
            print(f"  (warm-up skipped: {e})")

    def _clean_url(self, href):
        """Return a clean https://blog.naver.com/... URL, or None."""
        url = href.replace('m.blog.naver.com', 'blog.naver.com')
        m = re.search(r'(https?://blog\.naver\.com/[^\s&?"\'#]+)', url)
        if m:
            return m.group(1).split('?')[0]
        m = re.search(r'(blog\.naver\.com/[^\s&?"\'#]+)', url)
        if m:
            return 'https://' + m.group(1).split('?')[0]
        return None

    def _username(self, url):
        """Extract Naver blog username from a clean URL."""
        m = re.search(r'blog\.naver\.com/([^/?#]+)', url)
        if not m:
            return None
        u = m.group(1)
        if u and u not in EXCLUDE_PATHS and not u.startswith('?'):
            return u
        return None

    def _parse_page(self, html):
        """Extract new (username, url, title) tuples from a Naver blog search HTML page."""
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        seen_urls = {r['blog_url'] for r in self.results}

        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'blog.naver.com' not in href:
                continue

            url = self._clean_url(href)
            if not url or url in seen_urls:
                continue

            username = self._username(url)
            if not username:
                continue

            title = link.get_text(strip=True) or "No title"

            self.results.append({
                'username': username,
                'blog_url': url,
                'title': title[:120],
                'search_query': self.current_query,
            })
            seen_urls.add(url)
            print(f"  ✅ @{username}: {title[:65]}")
            found += 1

        return found

    def search_naver_blog(self, query, num_pages=3):
        """Search Naver blog search and collect results."""
        self._warm_up()
        base = "https://search.naver.com/search.naver"

        for page in range(num_pages):
            start = page * 10 + 1
            print(f"  Fetching page {page + 1} (start={start})...")
            try:
                resp = self.session.get(
                    base,
                    params={'where': 'blog', 'query': query, 'start': start},
                    headers=self._headers(referer="https://www.naver.com"),
                    timeout=15
                )
                resp.raise_for_status()

                found = self._parse_page(resp.text)
                print(f"  → {found} new result(s) on page {page + 1}")

                if found == 0 and page > 0:
                    print("  No more results — stopping early.")
                    break

            except requests.HTTPError as e:
                print(f"  HTTP {e.response.status_code} on page {page + 1}")
                if e.response.status_code == 429:
                    print("  Rate limited — waiting 30s...")
                    time.sleep(30)
                continue
            except Exception as e:
                print(f"  Error: {e}")
                continue

            time.sleep(random.uniform(2, 4))

    def save_to_csv(self, filename='naver_blogs.csv'):
        if not self.results:
            print("No results to save!")
            return

        # Deduplicate by blog_url before saving
        seen = set()
        unique = []
        for r in self.results:
            if r['blog_url'] not in seen:
                seen.add(r['blog_url'])
                unique.append(r)

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'blog_url', 'title', 'search_query'])
            writer.writeheader()
            writer.writerows(unique)
        print(f"\n Saved {len(unique)} results to {filename}")

        usernames = sorted(set(r['username'] for r in unique))
        with open('usernames.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(usernames))
        print(f" Saved {len(usernames)} unique usernames to usernames.txt")

    def print_stats(self):
        if not self.results:
            return
        unique_users = set(r['username'] for r in self.results)
        print("\n" + "=" * 100)
        print(f"   Total URL Results : {len(self.results)}")
        print(f"   Unique Bloggers   : {len(unique_users)}")
        print(f"   Queries Run       : {len(set(r['search_query'] for r in self.results))}")
        print("=" * 100)
        print("\n Sample Results:")
        shown = set()
        for r in self.results:
            if r['username'] not in shown:
                print(f"  • @{r['username']}: {r['title'][:60]}")
                shown.add(r['username'])
            if len(shown) >= 5:
                break

if __name__ == "__main__":
    extractor = NaverBlogExtractor()

    queries = [
        '부산 체험단',
        '부산 체험단 모집',
        '부산 블로그 체험단',
        '해운대 체험단',
        '해운대 체험단 모집',
        '해운대 블로그 체험단',
    ]

    print("Searching Naver Blog directly...\n")
    for query in queries:
        extractor.current_query = query
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print('='*50)
        extractor.search_naver_blog(query, num_pages=3)

    extractor.save_to_csv('naver_blogs.csv')
    extractor.print_stats()

    if extractor.results:
        all_usernames = sorted(set(r['username'] for r in extractor.results))
        print(f"\n All {len(all_usernames)} unique usernames:")
        for u in all_usernames:
            print(f"  @{u}")
