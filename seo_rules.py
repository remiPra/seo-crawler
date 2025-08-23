# seo_rules.py
from dataclasses import dataclass
from typing import List, Dict, Any
import re

# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURES DE DONNÉES
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Issue:
    rule_id: str
    topic: str
    severity: str
    message: str
    evidence: Dict[str, Any] | None = None

@dataclass
class RuleResult:
    issues: List[Issue]
    score_delta: int

# ──────────────────────────────────────────────────────────────────────────────
# FONCTIONS HELPER
# ──────────────────────────────────────────────────────────────────────────────
def _present(x) -> bool: return bool(x and str(x).strip())
def _strlen(x: str) -> int: return len(x or "")
def _ratio(a: int, b: int) -> float: return (a / b) if b else 0.0

# ──────────────────────────────────────────────────────────────────────────────
# DÉFINITION DE TOUTES LES RÈGLES D'ANALYSE
# ──────────────────────────────────────────────────────────────────────────────

# --- BLOC CRITIQUE & FONDAMENTAUX ---
def r_meta_title_desc_canonical(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    title = (soup.title.string or "").strip() if soup.title else ""
    desc = (soup.find("meta", attrs={"name": "description"}) or {}).get("content", "")
    canonical = (soup.find("link", rel="canonical") or {}).get("href", "")
    
    if not _present(title):
        issues.append(Issue("META_TITLE_MISSING","Meta","error","Title manquant"))
        delta -= 12
    elif not (50 <= _strlen(title) <= 70):
        issues.append(Issue("META_TITLE_LENGTH","Meta","warn",f"Title hors zone 50–70 caractères ({_strlen(title)})"))
        delta -= 6
    else: delta += 2
    
    if not _present(desc):
        issues.append(Issue("META_DESC_MISSING","Meta","warn","Meta description manquante"))
        delta -= 6
    elif not (120 <= _strlen(desc) <= 160):
        issues.append(Issue("META_DESC_LENGTH","Meta","info",f"Meta description hors zone 120–160 ({_strlen(desc)})"))
        delta -= 2
    else: delta += 2

    if not _present(canonical):
        issues.append(Issue("CANONICAL_MISSING","Meta","warn","Lien canonique absent"))
        delta -= 4
    else: delta += 1
    
    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and "noindex" in (robots.get("content") or "").lower():
        issues.append(Issue("ROBOTS_NOINDEX","Meta","error","noindex présent sur une page crawlée"))
        delta -= 30
        
    return RuleResult(issues, delta)

def r_headings_revolutionary_analysis(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    headings = [{'level': int(h.name[1]), 'text': h.get_text(strip=True)} for h in soup.find_all(re.compile('^h[1-6]$')) if h.get_text(strip=True)]
    
    if not headings:
        return RuleResult([Issue("HEADINGS_NONE", "Hn", "error", "Aucune balise H1-H6 détectée")], -20)
        
    h1s = [h for h in headings if h['level'] == 1]
    if not h1s:
        issues.append(Issue("H1_MISSING", "Hn", "error", "H1 manquant, c'est critique !"))
        delta -= 15
    elif len(h1s) > 1:
        issues.append(Issue("H1_MULTIPLE", "Hn", "error", f"{len(h1s)} H1 détectés, un seul est permis."))
        delta -= 10
    else:
        issues.append(Issue("H1_OK", "Hn", "info", "Excellent, un seul H1 est présent."))
        delta += 3
        
    for i in range(1, len(headings)):
        if headings[i]['level'] > headings[i-1]['level'] + 1:
            issues.append(Issue("HIERARCHY_LOGIC_BROKEN", "Hn", "warn", "Saut de niveau de titre détecté (ex: H2 vers H4)"))
            delta -= 3
            break
            
    return RuleResult(issues, delta)

# --- BLOC STRATÉGIQUE 2025 (AEO, E-A-T, CWV) ---
def r_aeo_ai_meta_tags(soup, html, url, headers, extras) -> RuleResult:
    aeo_tags_count = sum(1 for name in ["ai-content-declaration", "llm-friendly", "content-summary"] if soup.find("meta", attrs={"name": name}))
    if aeo_tags_count > 0:
        return RuleResult([Issue("AEO_EARLY_ADOPTER", "AEO", "info", f"Excellent, {aeo_tags_count} meta tag(s) AEO 2025 détecté(s).")], 5)
    return RuleResult([Issue("AEO_NO_OPTIMIZATION", "AEO", "warn", "Aucune optimisation AEO (meta tags IA) détectée.")], -3)

def r_eat_authority_signals(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    legal_keywords = {"privacy", "terms", "legal", "mentions", "about", "contact"}
    found_legal = {kw for link in soup.find_all("a", href=True) for kw in legal_keywords if kw in (link.get("href", "") + link.get_text()).lower()}
    
    if len(found_legal) < 4:
        issues.append(Issue("EAT_LEGAL_MISSING", "Trust", "error", f"Pages légales manquantes ({len(found_legal)}/4 essentiels trouvés). C'est un signal de confiance faible."))
        delta -= 8
    else:
        issues.append(Issue("EAT_LEGAL_OK", "Trust", "info", "Bonne base de pages légales trouvée."))
        delta += 8
        
    jsonlds = " ".join([s.string or "" for s in soup.find_all("script", type="application/ld+json")])
    if '"@type":"Person"' in jsonlds:
        issues.append(Issue("EAT_AUTHOR_SCHEMA", "Authority", "info", "Schema Person détecté, bon pour l'expertise."))
        delta += 5
    else:
        issues.append(Issue("EAT_AUTHOR_SCHEMA_MISSING", "Authority", "warn", "Schema Person manquant pour déclarer l'expertise."))
        delta -= 3
        
    return RuleResult(issues, delta)

def r_core_web_vitals_advanced(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    if soup.find("img", attrs={"fetchpriority": "high"}):
        delta += 4
        issues.append(Issue("CWV_FETCHPRIORITY_IMG", "Perf", "info", "Image LCP optimisée avec fetchpriority=high."))
    else:
        issues.append(Issue("CWV_FETCHPRIORITY_MISSING", "Perf", "warn", "L'image principale (LCP) devrait utiliser fetchpriority=high."))
        delta -= 2
        
    imgs = soup.find_all("img")
    if imgs and len([i for i in imgs if i.get("width") and i.get("height")]) / len(imgs) < 0.8:
        issues.append(Issue("CWV_IMG_DIMENSIONS_MISSING", "Perf", "warn", "La plupart des images n'ont pas de dimensions explicites (width/height), risque de CLS."));
        delta -= 3
    else:
        delta += 2
        
    return RuleResult(issues, delta)

def r_schema_advanced_2025(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    jsonlds = soup.find_all("script", type="application/ld+json")
    if not jsonlds:
        return RuleResult([Issue("SCHEMA_NO_JSONLD", "AEO", "warn", "Aucun JSON-LD détecté, une opportunité majeure manquée.")], -3)
        
    all_content = " ".join([script.string or "" for script in jsonlds])
    aeo_schemas = {"FAQPage": 5, "HowTo": 4, "Article": 3}
    found_aeo = [s for s in aeo_schemas if s in all_content]
    
    if found_aeo:
        issues.append(Issue("SCHEMA_AEO_OPTIMIZED", "AEO", "info", f"Excellent, la page est optimisée pour l'IA avec les schémas : {', '.join(found_aeo)}."))
        for s in found_aeo: delta += aeo_schemas[s]
    else:
        issues.append(Issue("SCHEMA_AEO_MISSING", "AEO", "warn", "Aucun schéma AEO (FAQ, HowTo...) détecté."))
        delta -= 3
        
    return RuleResult(issues, delta)

# --- BLOC CONTENU, MOBILE & INTERNATIONAL ---
def r_internationalization_mobile_pwa(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    if soup.find("html") and soup.find("html").get("lang"):
        delta += 2
    else:
        issues.append(Issue("I18N_LANG_MISSING", "i18n", "error", "L'attribut 'lang' est manquant sur la balise <html>."))
        delta -= 3
        
    if not soup.find("meta", attrs={"name": "viewport"}):
        issues.append(Issue("MOBILE_VIEWPORT_MISSING", "Mobile", "error", "La meta viewport est manquante, crucial pour le mobile."))
        delta -= 5
    else:
        delta += 2
        
    if soup.find("link", rel="manifest"):
        issues.append(Issue("PWA_READY", "Mobile", "info", "La page semble être une PWA (manifest trouvé)."))
        delta += 3
        
    return RuleResult(issues, delta)

def r_content_advanced_analysis(soup, html, url, headers, extras) -> RuleResult:
    issues, delta = [], 0
    main = soup.find("main") or soup.body or soup
    text = main.get_text(" ", strip=True)
    word_count = len(re.findall(r'\b\w+\b', text))
    
    if word_count < 300:
        issues.append(Issue("CONTENT_SHORT", "Content", "warn", f"Contenu court ({word_count} mots), visez au moins 300 mots."));
        delta -= 3
    elif word_count >= 1000:
        issues.append(Issue("CONTENT_EXCELLENT_LENGTH", "Content", "info", f"Contenu approfondi ({word_count} mots)."));
        delta += 5
    else:
        delta += 2
        
    return RuleResult(issues, delta)

# --- BLOC TECHNIQUE & ACCESSIBILITÉ ---
def r_social_og_twitter(soup, html, url, headers, extras) -> RuleResult:
    delta = 0
    if soup.find("meta", property="og:title") and soup.find("meta", property="og:image"):
        delta += 1
    else:
        delta -= 2
    if soup.find("meta", attrs={"name":"twitter:card"}):
        delta += 1
    else:
        delta -= 1
    return RuleResult([], delta)

def r_links_basic(soup, html, url, headers, extras) -> RuleResult:
    if not any(a.get("href", "").startswith(("/", "#")) for a in soup.find_all("a", href=True)):
        return RuleResult([Issue("LINKS_INTERNAL_ZERO","Links","warn","Aucun lien interne détecté.")], -3)
    return RuleResult([], 0)

def r_images_alt_text(soup, html, url, headers, extras) -> RuleResult:
    noalt = sum(1 for i in soup.find_all("img") if not (i.get("alt") or "").strip())
    if noalt > 0:
        return RuleResult([Issue("IMG_NOALT","Access","warn",f"{noalt} image(s) sans texte alternatif (alt).")], -min(10, noalt))
    return RuleResult([], 2)

def r_images_format(soup, html, url, headers, extras) -> RuleResult:
    if any('.webp' in i.get('src','') or '.avif' in i.get('src','') for i in soup.find_all("img", src=True)):
        return RuleResult([], 1)
    return RuleResult([Issue("IMG_FORMATS","Perf","info","Aucune image WebP/AVIF détectée, formats plus performants.")], 0)

def r_access_landmarks(soup, html, url, headers, extras) -> RuleResult:
    if all(soup.find(tag) for tag in ["main", "nav", "header", "footer"]):
        return RuleResult([], 1)
    return RuleResult([Issue("LANDMARKS_MISSING", "Access", "info", "Balises sémantiques (main, nav...) manquantes.")], 0)

# --- RÈGLES SPÉCIALES (appelées depuis le crawler) ---
def r_security_headers(headers) -> RuleResult:
    missing = [key for key in ["content-security-policy", "x-frame-options"] if key.lower() not in headers]
    if missing:
        return RuleResult([Issue("SEC_HEADERS","Security","info",f"Headers de sécurité HTTP manquants: {', '.join(missing)}") ], -4)
    return RuleResult([], 3)

def r_aeo_llm_files(extras) -> RuleResult:
    if not extras: return RuleResult([], 0)
    miss = [f for f, s in [("llms.txt", "llms_txt_status"), ("ai.txt", "ai_txt_status")] if extras.get(s) != 200]
    if miss:
        return RuleResult([Issue("AEO_LLM_FILES","AEO","info",f"Fichiers AEO pour les IA non trouvés: {', '.join(miss)}") ], -1)
    return RuleResult([], 2)

# ──────────────────────────────────────────────────────────────────────────────
# LISTE FINALE DES RÈGLES À EXÉCUTER
# ──────────────────────────────────────────────────────────────────────────────
RULES = [
    # --- BLOC CRITIQUE & FONDAMENTAUX ---
    r_meta_title_desc_canonical,
    r_headings_revolutionary_analysis,
    
    # --- BLOC STRATÉGIQUE 2025 (AEO, E-A-T, CWV) ---
    r_aeo_ai_meta_tags,
    r_eat_authority_signals,
    r_core_web_vitals_advanced,
    r_schema_advanced_2025,
    
    # --- BLOC CONTENU, MOBILE & INTERNATIONAL ---
    r_internationalization_mobile_pwa,
    r_content_advanced_analysis,
    
    # --- BLOC TECHNIQUE & ACCESSIBILITÉ ---
    r_social_og_twitter,
    r_links_basic,
    r_images_alt_text,
    r_images_format,
    r_access_landmarks,
]