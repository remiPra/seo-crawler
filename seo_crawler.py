# seo_crawler.py
import re, time, urllib.parse, requests
from collections import deque
from bs4 import BeautifulSoup

UA = {"User-Agent": "SEO-Tool/1.0 (+https://example.com/bot)"}  # customise si tu veux

def _same_host(u, host):
    return urllib.parse.urlparse(u).netloc == host

def _abs(base, href):
    return urllib.parse.urljoin(base, href)

def _report(url, html, res):
    s = BeautifulSoup(html, "lxml")
    title = (s.title.string or "").strip() if s.title and s.title.string else ""
    md = s.find("meta", attrs={"name": "description"})
    meta_desc = (md.get("content") if md else "") or ""
    robots = s.find("meta", attrs={"name": "robots"})
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
        "url": res.url, "status": res.status_code,
        "title": title, "title_length": len(title),
        "meta_description": meta_desc, "meta_description_length": len(meta_desc),
        "meta_robots": meta_robots,
        "canonical": canonical,
        "h1_count": len(h1s), "h1": h1s[0] if h1s else "",
        "h2_count": len(h2s),
        "images_count": len(imgs), "images_without_alt": img_noalt,
        "og_title": og_title, "og_image": og_image, "twitter_card": tw_card,
        "word_count": word_count, "approx_html_size": len(html),
        "score": max(0, score),
    }

def crawl(start_url: str, max_pages: int = 60):
    parsed = urllib.parse.urlparse(start_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.netloc

    # robots.txt très simple : si Disallow: / (sans Allow /) on stoppe
    try:
        r = requests.get(base + "/robots.txt", headers=UA, timeout=6)
        if r.ok and "Disallow: /" in r.text and "Allow: /" not in r.text:
            return [{"url": base, "status": 999, "error": "blocked by robots.txt"}]
    except Exception:
        pass

    seen, out = set(), []
    q = deque([start_url])

    while q and len(out) < max_pages:
        url = q.popleft()
        if url in seen: 
            continue
        seen.add(url)

        try:
            res = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        except Exception:
            out.append({"url": url, "status": 0, "error": "fetch-failed"})
            continue

        if res.status_code >= 400:
            out.append({"url": url, "status": res.status_code, "error": True})
            continue

        rpt = _report(url, res.text or "", res)
        out.append(rpt)

        # liens internes
        s = BeautifulSoup(res.text or "", "lxml")
        for a in s.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:")): 
                continue
            link = _abs(url, href)
            if _same_host(link, host) and link not in seen:
                q.append(link)

        time.sleep(0.2)  # politesse
    return out
