# seo_crawler_js.py
import re
from collections import deque
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

UA = "SEO-Tool/1.0 (+https://example.com/bot)"

def _report(url, html):
    s = BeautifulSoup(html, "lxml")
    title = (s.title.string or "").strip() if s.title and s.title.string else ""
    md = s.find("meta", attrs={"name":"description"})
    meta_desc = (md.get("content") if md else "") or ""
    robots = s.find("meta", attrs={"name":"robots"})
    meta_robots = ((robots.get("content") if robots else "") or "").lower()
    canonical = ""
    link_canon = s.find("link", rel=lambda v: v and "canonical" in v)
    if link_canon:
        canonical = (link_canon.get("href") or "").strip()

    h1s = [h.get_text(strip=True) for h in s.find_all("h1")]
    h2s = [h.get_text(strip=True) for h in s.find_all("h2")]
    imgs = s.find_all("img")
    img_noalt = sum(1 for i in imgs if not (i.get("alt") or "").strip())
    og_title = (s.find("meta", attrs={"property":"og:title"}) or {}).get("content","") or ""
    og_image = (s.find("meta", attrs={"property":"og:image"}) or {}).get("content","") or ""
    tw_card = (s.find("meta", attrs={"name":"twitter:card"}) or {}).get("content","") or ""
    text = s.get_text(" ", strip=True)
    word_count = len(re.findall(r"\w+", text))

    score = 100
    if not title or len(title) < 10 or len(title) > 70: score -= 10
    if not meta_desc or len(meta_desc) < 50 or len(meta_desc) > 170: score -= 8
    if len(h1s) != 1: score -= 8
    if img_noalt > 0: score -= min(10, img_noalt)
    if not og_title or not og_image: score -= 5
    if not canonical: score -= 4
    if "noindex" in meta_robots: score -= 30

    return {
        "url": url, "title": title, "title_length": len(title),
        "meta_description": meta_desc, "meta_description_length": len(meta_desc),
        "meta_robots": meta_robots, "canonical": canonical,
        "h1_count": len(h1s), "h1": h1s[0] if h1s else "",
        "h2_count": len(h2s),
        "images_count": len(imgs), "images_without_alt": img_noalt,
        "og_title": og_title, "og_image": og_image, "twitter_card": tw_card,
        "word_count": word_count, "approx_html_size": len(html),
        "score": max(0, score),
    }

async def crawl_js(start_url: str, max_pages: int = 40):
    parsed = urlparse(start_url)
    host = parsed.netloc
    seen, out = set(), []
    q = deque([start_url])

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(user_agent=UA)
        page = await context.new_page()

        while q and len(out) < max_pages:
            url = q.popleft()
            if url in seen:
                continue
            seen.add(url)
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                final_url = page.url
            except Exception:
                out.append({"url": url, "status": 0, "error": "render-failed"})
                continue

            rpt = _report(final_url, html)
            out.append(rpt)

            s = BeautifulSoup(html, "lxml")
            for a in s.find_all("a", href=True):
                link = urljoin(final_url, a["href"].strip())
                if urlparse(link).netloc == host and link not in seen:
                    q.append(link)

        await browser.close()
    return out
