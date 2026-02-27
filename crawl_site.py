import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import time
import json
from collections import deque
import urllib.robotparser
from tqdm import tqdm

# Try to import selenium for JavaScript rendering
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        from webdriver_manager.chrome import ChromeDriverManager

        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    print("[WARNING] Selenium not available. JavaScript content may not be captured.")
    print("[INFO] Install selenium: pip install selenium webdriver-manager")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
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
MAX_PAGES = 0  # 0 = no limit, crawl all pages
REQUEST_DELAY = 0.5  # seconds - reduced for faster crawling
OUTPUT_FILE = "crawled_pages.jsonl"
MIN_TEXT_LENGTH = 100
DEBUG = True
USE_SELENIUM = True  # Set to True to use headless browser for JavaScript content


def is_same_domain(root, url):
    root_parsed = urlparse(root)
    url_parsed = urlparse(url)
    # Also compare without www prefix
    root_netloc = root_parsed.netloc.replace("www.", "")
    url_netloc = url_parsed.netloc.replace("www.", "")
    return root_netloc == url_netloc


def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc
    # Remove www prefix if present
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path or "/"
    # Remove trailing slash except for root
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = parsed.query
    return urlunparse((scheme, netloc, path, "", query, ""))


def get_robots_parser(root):
    rp = urllib.robotparser.RobotFileParser()
    robots_url = urljoin(root, "/robots.txt")
    try:
        rp.set_url(robots_url)
        rp.read()
        if DEBUG:
            print(f"[DEBUG] Robots.txt parsed for {root}")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Could not read robots.txt: {e}")
    return rp


def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    # Remove unwanted elements
    for s in soup(
        ["script", "style", "header", "footer", "nav", "aside", "iframe", "noscript"]
    ):
        s.decompose()

    # Also remove elements with hidden class or style
    for elem in soup.find_all(
        style=lambda x: x and "display:none" in x.replace(" ", "")
    ):
        elem.decompose()
    for elem in soup.find_all(class_=lambda x: x and "hidden" in x):
        elem.decompose()

    texts = []
    # Find more content types
    for tag in soup.find_all(
        [
            "p",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "td",
            "th",
            "span",
            "div",
            "article",
            "section",
            "label",
            "a",
        ]
    ):
        t = tag.get_text(separator=" ", strip=True)
        # Filter out very short texts and navigation-like content
        if t and len(t) > 10 and not t.startswith("Cookie"):
            texts.append(t)
    return "\n".join(texts)


def get_page_content(url, driver=None, use_selenium_flag=True):
    """Get page content - uses Selenium if available and enabled, otherwise falls back to requests"""

    if use_selenium_flag and driver:
        try:
            driver.get(url)
            # Wait for page to load - wait for body or specific element
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # Give extra time for dynamic content to load
            time.sleep(3)
            return driver.page_source, True
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Selenium error for {url}: {str(e)[:80]}")
            return None, False
    else:
        # Fallback to requests
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text, True
            return None, False
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Request error for {url}: {str(e)[:80]}")
            return None, False


def crawl(root):
    root = normalize_url(root)
    rp = get_robots_parser(root)

    # Initialize Selenium driver if available
    driver = None
    use_selenium = False

    if USE_SELENIUM and SELENIUM_AVAILABLE:
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"--user-agent={USER_AGENT}")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            # Prevent detection
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)

            # Use webdriver-manager if available for automatic driver management
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    if DEBUG:
                        print(f"[DEBUG] webdriver-manager failed: {str(e)[:80]}")
                    driver = webdriver.Chrome(options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)

            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
                """
                },
            )
            use_selenium = True
            if DEBUG:
                print("[DEBUG] Selenium WebDriver initialized successfully")
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Could not initialize Selenium: {str(e)[:100]}")
            print(
                "[INFO] Falling back to requests-only mode (JavaScript content may be missing)"
            )

    q = deque([root])
    seen = set([root])
    results = []

    if DEBUG:
        print(f"[DEBUG] Starting crawl from: {root}")
        print(f"[DEBUG] Using Selenium: {use_selenium}")

    pbar = tqdm(
        total=MAX_PAGES if MAX_PAGES > 0 else None,
        desc="Crawling ISMT site",
        unit="page",
    )
    skipped_reasons = {
        "robots": 0,
        "status": 0,
        "content_type": 0,
        "too_short": 0,
        "exception": 0,
        "no_driver": 0,
    }

    while q:
        url = q.popleft()

        try:
            html_content, success = get_page_content(url, driver, use_selenium)

            if not success or html_content is None:
                pbar.update(1)
                skipped_reasons["status"] += 1
                continue

            # Check for redirect - if redirected to different domain, skip
            if driver:
                final_url = driver.current_url
            else:
                final_url = url

            if not is_same_domain(root, final_url):
                if DEBUG:
                    print(
                        f"[DEBUG] Redirected to different domain: {url} -> {final_url}"
                    )
                pbar.update(1)
                skipped_reasons["status"] += 1
                continue

            text = extract_visible_text(html_content)

            # More lenient text length check
            if len(text.strip()) < MIN_TEXT_LENGTH:
                if DEBUG:
                    print(
                        f"[DEBUG] Text too short for {url}: {len(text.strip())} chars"
                    )
                pbar.update(1)
                skipped_reasons["too_short"] += 1
                continue

            results.append({"url": url, "text": text})
            if DEBUG:
                print(f"[DEBUG] Saved page: {url} ({len(text)} chars)")
            pbar.update(1)

            soup = BeautifulSoup(html_content, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].split("#")[0]
                # Skip empty hrefs
                if not href or href in ["", "/"]:
                    continue
                joined = urljoin(url, href)
                norm = normalize_url(joined)
                if norm not in seen and is_same_domain(root, norm):
                    seen.add(norm)
                    q.append(norm)

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Exception for {url}: {str(e)[:100]}")
            pbar.update(1)
            skipped_reasons["exception"] += 1
            continue
    pbar.close()

    # Clean up driver
    if driver:
        try:
            driver.quit()
        except:
            pass

    if DEBUG:
        print(f"[DEBUG] Skipped reasons: {skipped_reasons}")
        print(f"[DEBUG] Total URLs seen: {len(seen)}")
        print(f"[DEBUG] Queue remaining: {len(q)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            json.dump(r, f, ensure_ascii=False)
            f.write("\n")
    print(f"[DONE] Saved {len(results)} pages to {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl("https://ismt.edu.np/")
