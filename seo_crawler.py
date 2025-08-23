# seo_crawler.py (Version "Bulletproof" pour le débogage)
import re, time, urllib.parse, requests
from collections import deque
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from seo_rules import RULES, r_security_headers, r_aeo_llm_files

UA_STR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
UA = {"User-Agent": UA_STR}

_AEO_CACHE: Dict[str, Dict[str, int]] = {}

def _head_headers(url: str) -> Dict[str,str]:
    try:
        r = requests.head(url, headers=UA, timeout=10, allow_redirects=True)
        return {k.lower(): v for k, v in r.headers.items()}
    except Exception:
        return {}

def _test_aeo_files(base: str, host: str) -> Dict[str,int]:
    if host in _AEO_CACHE: return _AEO_CACHE[host]
    res = {}
    for path, key in [("/llms.txt","llms_txt_status"),("/ai.txt","ai_txt_status")]:
        try:
            rr = requests.get(base+path, headers=UA, timeout=10, allow_redirects=True)
            res[key] = rr.status_code
        except Exception:
            res[key] = 0
    _AEO_CACHE[host] = res
    return res

def _legacy_fields(url: str, html: str, res) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    md = soup.find("meta", attrs={"name":"description"})
    meta_desc = (md.get("content") if md else "") or ""
    robots = soup.find("meta", attrs={"name":"robots"})
    meta_robots = ((robots.get("content") if robots else "") or "").lower()
    canonical = (soup.find("link", rel="canonical") or {}).get("href", "").strip()
    
    headings = [{'level': int(h.name[1]), 'text': h.get_text(strip=True)} 
                for h in soup.find_all(re.compile('^h[1-6]$')) if h.get_text(strip=True)]

    h1s = [h for h in headings if h['level'] == 1]
    
    score = 100
    if not title or len(title) < 10 or len(title) > 70: score -= 10
    if not meta_desc or len(meta_desc) < 50 or len(meta_desc) > 170: score -= 8
    if len(h1s) != 1: score -= 8
    if not canonical: score -= 4
    if "noindex" in meta_robots: score -= 30

    return {
        "soup": soup,
        "fields": {
            "url": res.url,
            "status": res.status_code,
            "score_legacy": max(0, score),
            "extracted_data": {
                "title": f"{title} ({len(title)} car.)",
                "meta_description": f"{meta_desc[:120]}... ({len(meta_desc)} car.)",
                "canonical": canonical,
                "headings": headings,
            }
        }
    }

# --- CETTE FONCTION EST MAINTENANT "BULLETPROOF" ---
def _apply_rules(soup, html, url: str, headers: Dict[str,str], extras: Dict[str,int]) -> Dict[str,Any]:
    score_rules = 0
    recos: List[Dict[str,Any]] = []

    # On teste chaque règle dans un bloc try/except
    for rule in RULES:
        try:
            rr = rule(soup, html, url, headers, extras)
            score_rules += rr.score_delta
            recos.extend([i.__dict__ for i in rr.issues])
        except Exception as e:
            # Si une règle plante, on l'affiche dans le terminal et on continue
            print(f"--- ERREUR DANS UNE RÈGLE SEO ---")
            print(f"La règle '{rule.__name__}' a échoué sur l'URL: {url}")
            print(f"Erreur: {e}")
            print(f"---------------------------------")
            
    # Les règles spéciales sont aussi protégées
    try:
        rr_sec = r_security_headers(headers)
        score_rules += rr_sec.score_delta
        recos.extend([i.__dict__ for i in rr_sec.issues])
    except Exception as e:
        print(f"Erreur dans la règle r_security_headers: {e}")

    try:
        rr_aeo = r_aeo_llm_files(extras)
        score_rules += rr_aeo.score_delta
        recos.extend([i.__dict__ for i in rr_aeo.issues])
    except Exception as e:
        print(f"Erreur dans la règle r_aeo_llm_files: {e}")

    return {"score_rules": score_rules, "recommendations": recos}

def crawl(start_url: str, max_pages: int = 60):
    parsed = urllib.parse.urlparse(start_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    host = parsed.netloc

    try:
        r = requests.get(base + "/robots.txt", headers=UA, timeout=6)
        if r.ok and "Disallow: /" in r.text and "Allow: /" not in r.text:
            return {"pages": 0, "data": [{"url": base, "status": 999, "error": "blocked by robots.txt"}]}
    except Exception:
        pass

    extras = _test_aeo_files(base, host)
    seen, out = set(), []
    q = deque([start_url])

    while q and len(out) < max_pages:
        url = q.popleft()
        if url in seen: 
            continue
        seen.add(url)

        try:
            res = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        except Exception as e:
            out.append({"url": url, "status": 0, "error": f"fetch-failed: {e}"})
            continue

        if res.status_code >= 400:
            out.append({"url": url, "status": res.status_code, "error": True})
            continue

        legacy = _legacy_fields(url, res.text or "", res)
        headers = _head_headers(url)
        rules_part = _apply_rules(legacy["soup"], res.text or "", legacy["fields"]["url"], headers, extras)

        score_global = max(0, min(100, legacy["fields"]["score_legacy"] + rules_part["score_rules"]))

        record = {
            **legacy["fields"],
            "score_rules": rules_part["score_rules"],
            "score_global": score_global,
            "recommendations": rules_part["recommendations"],
        }
        out.append(record)

        s = legacy["soup"]
        for a in s.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            link = urllib.parse.urljoin(legacy["fields"]["url"], href.split('#')[0].split('?')[0])
            if urllib.parse.urlparse(link).netloc == host and link not in seen:
                q.append(link)

        time.sleep(0.2)
        
    return out
