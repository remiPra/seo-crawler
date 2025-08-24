# seo_analyzer.py
import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List

# Liste de mots vides (stop words) en français pour l'analyse de contenu
FRENCH_STOP_WORDS = set([
    'a', 'ai', 'ait', 'au', 'aux', 'avec', 'ce', 'ces', 'comme', 'dans', 'de', 'des', 
    'du', 'elle', 'en', 'est', 'et', 'eux', 'il', 'je', 'la', 'le', 'les', 'leur', 'lui', 
    'ma', 'mais', 'me', 'même', 'mes', 'moi', 'mon', 'ne', 'nos', 'notre', 'nous', 'on', 
    'ou', 'par', 'pas', 'pour', 'qu', 'que', 'qui', 'sa', 'se', 'ses', 'son', 'sur', 
    'ta', 'te', 'tes', 'toi', 'ton', 'tu', 'un', 'une', 'vos', 'votre', 'vous', 'c', 'd', 
    'j', 'l', 'm', 'n', 's', 't', 'y', 'à', 'ça', 'ès', 'été', 'être', 'eu', 'ont', 'sont'
])


def create_check(title, score, value, message):
    """Crée une structure de vérification standard."""
    return {"title": title, "score": score, "value": value, "message": message}

def check_structure(html_content, soup):
    """Vérifie la structure générale du document HTML."""
    checks = []
    # DOCTYPE
    doctype = soup.doctype if hasattr(soup, 'doctype') and soup.doctype else None
    is_html5 = doctype and 'html' in str(doctype).lower()
    checks.append(create_check(
        "DOCTYPE HTML5",
        1 if is_html5 else 0,
        "<!DOCTYPE html>" if is_html5 else "Non trouvé ou incorrect",
        "La déclaration DOCTYPE HTML5 est essentielle pour le rendu moderne."
    ))
    # Lang
    lang = soup.html.get('lang')
    checks.append(create_check(
        "Attribut Lang",
        1 if lang else 0,
        lang or "Non défini",
        "L'attribut 'lang' aide les moteurs de recherche à comprendre la langue de la page."
    ))
    # Charset
    charset = soup.find('meta', charset=True)
    is_utf8 = charset and charset.get('charset').lower() == 'utf-8'
    checks.append(create_check(
        "Encodage UTF-8",
        1 if is_utf8 else 0,
        "UTF-8" if is_utf8 else "Non trouvé ou incorrect",
        "UTF-8 est l'encodage standard pour une compatibilité maximale des caractères."
    ))
    # Viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    is_viewport_ok = viewport and 'width=device-width' in viewport.get('content')
    checks.append(create_check(
        "Meta Viewport",
        1 if is_viewport_ok else 0,
        viewport.get('content') if viewport else "Non trouvé",
        "Le viewport est crucial pour le design responsive et le SEO mobile."
    ))
    return checks

def check_head_tags(soup):
    """Vérifie les balises essentielles dans le <head>."""
    checks = []
    # Title
    title = soup.find('title')
    title_text = title.get_text(strip=True) if title else ""
    title_len = len(title_text)
    title_score = 1 if 10 < title_len < 65 else 0.5 if title_text else 0
    checks.append(create_check(
        "Balise Title",
        title_score,
        f"{title_text} ({title_len} chars)",
        "Le titre doit être unique, descriptif et faire entre 10 et 65 caractères."
    ))
    # Meta Description
    desc = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc.get('content', '').strip() if desc else ""
    desc_len = len(desc_text)
    desc_score = 1 if 70 < desc_len < 160 else 0.5 if desc_text else 0
    checks.append(create_check(
        "Meta Description",
        desc_score,
        f"{desc_text[:100]}... ({desc_len} chars)",
        "La description doit être engageante et faire entre 70 et 160 caractères."
    ))
    # Canonical URL
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    checks.append(create_check(
        "URL Canonique",
        1 if canonical else 0.5,
        canonical.get('href') if canonical else "Non trouvée",
        "La balise canonique évite les problèmes de contenu dupliqué. Absente mais pas toujours requise."
    ))
    # Favicon
    favicon = soup.find('link', rel=lambda r: r and 'icon' in r)
    checks.append(create_check(
        "Favicon",
        1 if favicon else 0,
        "Trouvée" if favicon else "Non trouvée",
        "Le favicon améliore la reconnaissance de la marque dans les onglets et les favoris."
    ))
    return checks

def check_body_structure(soup):
    """Vérifie la hiérarchie des titres et l'utilisation des balises sémantiques."""
    checks = []
    # H1
    h1s = soup.find_all('h1')
    h1_count = len(h1s)
    h1_texts = [h.get_text(strip=True) for h in h1s]
    h1_score = 1 if h1_count == 1 else 0
    checks.append(create_check(
        "Balise H1 Unique",
        h1_score,
        f"{h1_count} balise(s) trouvée(s): {h1_texts}",
        "Une page doit avoir une et une seule balise H1 pour définir son sujet principal."
    ))
    # Hiérarchie Hn
    headings = [int(h.name[1]) for h in soup.find_all(re.compile(r'^h[1-6]$'))]
    hierarchy_ok = all(headings[i] <= headings[i+1] for i in range(len(headings)-1))
    checks.append(create_check(
        "Hiérarchie des Titres",
        1 if hierarchy_ok else 0.5,
        "Respectée" if hierarchy_ok else "Non respectée",
        "Les niveaux de titres (H1 > H2 > H3) ne doivent pas être sautés pour une bonne structure."
    ))
    # Balises sémantiques
    semantic_tags = {'<main>': bool(soup.main), '<nav>': bool(soup.nav), '<footer>': bool(soup.footer)}
    semantic_score = sum(semantic_tags.values()) / len(semantic_tags)
    found_tags = [tag for tag, found in semantic_tags.items() if found]
    checks.append(create_check(
        "Balises Sémantiques",
        semantic_score,
        f"Trouvées : {found_tags}" if found_tags else "Aucune",
        "<main>, <nav>, <footer> aident les robots à comprendre la structure de la page."
    ))
    return checks

def check_content_analysis(soup):
    """Analyse le contenu textuel de la page."""
    checks = []
    # Word Count
    text = soup.get_text(separator=' ')
    words = re.findall(r'\b\w+\b', text.lower())
    word_count = len(words)
    content_score = 1 if word_count > 300 else 0.5
    checks.append(create_check(
        "Nombre de Mots",
        content_score,
        f"{word_count} mots",
        "Un contenu de plus de 300 mots est généralement mieux perçu pour le SEO."
    ))
    # Keyword analysis
    meaningful_words = [w for w in words if w not in FRENCH_STOP_WORDS and len(w) > 2]
    word_freq = {}
    for word in meaningful_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    checks.append(create_check(
        "Top Mots-Clés",
        1,
        str(top_keywords),
        "Les mots les plus fréquents (hors mots vides). Vérifiez qu'ils correspondent au sujet."
    ))
    return checks

def check_images(soup):
    """Vérifie l'optimisation des images."""
    checks = []
    images = soup.find_all('img')
    img_count = len(images)
    if img_count == 0:
        return [create_check("Images", 1, "0 image trouvée", "Pas d'images à analyser.")]
        
    alt_missing = sum(1 for i in images if not i.has_attr('alt'))
    lazy_loading_count = sum(1 for i in images if i.get('loading') == 'lazy')
    
    alt_score = (img_count - alt_missing) / img_count
    lazy_score = lazy_loading_count / img_count
    
    checks.append(create_check(
        "Texte Alternatif (Alt)",
        alt_score,
        f"{img_count - alt_missing} / {img_count} images ont un attribut 'alt'",
        "L'attribut 'alt' est crucial pour l'accessibilité et le SEO des images."
    ))
    checks.append(create_check(
        "Lazy Loading",
        lazy_score,
        f"{lazy_loading_count} / {img_count} images utilisent le chargement différé",
        "L'attribut 'loading=\"lazy\"' accélère le chargement initial de la page."
    ))
    return checks

def check_links(soup, base_url):
    """Analyse les liens internes, externes et leur qualité."""
    checks = []
    links = soup.find_all('a', href=True)
    internal, external, nofollow = 0, 0, 0
    bad_anchors = []
    
    for link in links:
        href = link.get('href')
        anchor_text = link.get_text(strip=True).lower()
        
        if any(bad in anchor_text for bad in ['cliquez ici', 'lire la suite', 'en savoir plus']):
            bad_anchors.append(anchor_text)
            
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc == urlparse(base_url).netloc:
            internal += 1
        else:
            external += 1
            if link.get('rel') and 'nofollow' in link.get('rel'):
                nofollow += 1
                
    checks.append(create_check(
        "Liens Internes", 1, f"{internal} liens",
        "Un bon maillage interne aide à la navigation et à la distribution du 'jus' SEO."
    ))
    checks.append(create_check(
        "Liens Externes", 1, f"{external} liens ({nofollow} en nofollow)",
        "Les liens externes peuvent apporter de la crédibilité, mais doivent être qualitatifs."
    ))
    checks.append(create_check(
        "Qualité des Ancres", 1 if not bad_anchors else 0.5,
        f"{len(bad_anchors)} ancres non descriptives trouvées" if bad_anchors else "Bonnes ancres",
        "Les textes des liens doivent être descriptifs et éviter les termes génériques."
    ))
    return checks

def check_social_tags(soup):
    """Vérifie la présence des balises Open Graph et Twitter Cards."""
    checks = []
    # Open Graph
    og_title = soup.find('meta', property='og:title')
    og_desc = soup.find('meta', property='og:description')
    og_image = soup.find('meta', property='og:image')
    og_score = 1 if og_title and og_desc and og_image else 0.5 if og_title else 0
    checks.append(create_check(
        "Balises Open Graph (Facebook)", og_score,
        "Complètes" if og_score == 1 else "Partielles" if og_score == 0.5 else "Absentes",
        "Essentielles pour un partage optimisé et visuel sur les réseaux sociaux."
    ))
    # Twitter Cards
    tw_card = soup.find('meta', attrs={'name': 'twitter:card'})
    tw_title = soup.find('meta', attrs={'name': 'twitter:title'})
    tw_score = 1 if tw_card and tw_title else 0
    checks.append(create_check(
        "Balises Twitter Cards", tw_score,
        "Présentes" if tw_score == 1 else "Absentes",
        "Assurent un affichage enrichi lors du partage de liens sur Twitter."
    ))
    return checks

def check_technical(html_content, soup):
    """Vérifie des points techniques comme la présence de JSON-LD et le ratio texte/code."""
    checks = []
    # JSON-LD Schema
    json_ld = soup.find('script', attrs={'type': 'application/ld+json'})
    is_valid_json = False
    if json_ld:
        try:
            json.loads(json_ld.string)
            is_valid_json = True
        except json.JSONDecodeError:
            is_valid_json = False
    checks.append(create_check(
        "Schema.org (JSON-LD)",
        1 if is_valid_json else 0.5 if json_ld else 0,
        "Valide" if is_valid_json else "Invalide" if json_ld else "Absent",
        "Les données structurées aident Google à comprendre le contenu et à créer des rich snippets."
    ))
    # Ratio Texte/Code
    text_length = len(soup.get_text())
    html_length = len(html_content)
    ratio = text_length / html_length if html_length > 0 else 0
    ratio_score = 1 if ratio > 0.15 else 0.5
    checks.append(create_check(
        "Ratio Texte/Code", ratio_score, f"{ratio:.2%}",
        "Un bon ratio (idéalement > 15%) indique une page riche en contenu plutôt qu'en code."
    ))
    return checks


def analyze_seo_page(url: str) -> Dict[str, Any]:
    """Fonction principale d'analyse SEO complète."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
    except requests.RequestException as e:
        return {"error": f"Impossible de récupérer l'URL : {e}", "success": False}

    all_checks = {
        "structure": check_structure(html_content, soup),
        "head": check_head_tags(soup),
        "body": check_body_structure(soup),
        "content": check_content_analysis(soup),
        "images": check_images(soup),
        "links": check_links(soup, url),
        "social": check_social_tags(soup),
        "technical": check_technical(html_content, soup),
    }

    total_score = 0
    total_checks = 0
    for category in all_checks.values():
        for check in category:
            total_score += check['score']
            total_checks += 1
            
    final_score = (total_score / total_checks) * 100 if total_checks > 0 else 0

    return {
        "url": url,
        "success": True,
        "overall_score": int(final_score),
        "results": all_checks
    }