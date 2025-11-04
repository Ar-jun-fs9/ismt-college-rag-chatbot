import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
from collections import deque
import urllib.robotparser
from tqdm import tqdm

USER_AGENT = "CollegeRAGBot/1.0 (+https://ismt.edu.np/)"
HEADERS = {"User-Agent": USER_AGENT}
MAX_PAGES = 300  # You can increase if needed
REQUEST_DELAY = 0.5  # seconds
OUTPUT_FILE = "crawled_pages.jsonl"


def is_same_domain(root, url):
    return urlparse(root).netloc == urlparse(url).netloc


def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc
    path = parsed.path or "/"
    return f"{scheme}://{netloc}{path}"


def get_robots_parser(root):
    rp = urllib.robotparser.RobotFileParser()
    robots_url = urljoin(root, "/robots.txt")
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        pass
    return rp


def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "header", "footer", "nav", "aside"]):
        s.decompose()
    texts = []
    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "td"]):
        t = tag.get_text(separator=" ", strip=True)
        if t:
            texts.append(t)
    return "\n".join(texts)


def crawl(root):
    root = normalize_url(root)
    rp = get_robots_parser(root)
    q = deque([root])
    seen = set([root])
    results = []

    pbar = tqdm(total=MAX_PAGES, desc="Crawling ISMT site", unit="page")
    while q and len(results) < MAX_PAGES:
        url = q.popleft()
        if not rp.can_fetch(USER_AGENT, url):
            pbar.update(1)
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            time.sleep(REQUEST_DELAY)
            if resp.status_code != 200 or "text/html" not in resp.headers.get(
                "Content-Type", ""
            ):
                pbar.update(1)
                continue
            text = extract_visible_text(resp.text)
            if len(text.strip()) < 200:
                pbar.update(1)
                continue
            results.append({"url": url, "text": text})
            pbar.update(1)

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].split("#")[0]
                joined = urljoin(url, href)
                norm = normalize_url(joined)
                if norm not in seen and is_same_domain(root, norm):
                    seen.add(norm)
                    q.append(norm)
        except Exception:
            pbar.update(1)
            continue
    pbar.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")
    print(f"[DONE] Saved {len(results)} pages to {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl("https://ismt.edu.np/")
