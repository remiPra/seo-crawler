# seo_analyzer.py
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List

# --- FONCTION UTILITAIRE (inchangée) ---
def create_check(title: str, score: float, value: Any, message: str, details: Any = None) -> Dict[str, Any]:
    """Crée une structure de vérification standard."""
    check = {"title": title, "score": score, "value": value, "message": message}
    if details:
        check["details"] = details
    return check

# --- FONCTIONS D'ANALYSE (ne font aucune requête réseau) ---

def analyze_meta_title(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Vérifie les balises meta et le titre, essentiels pour le SEO."""
    checks = []
    
    # 1. Balise Title
    title_tag = soup.find('title')
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    title_len = len(title_text)
    if not title_text:
        score, msg = 0, "La balise <title> est manquante. C'est un élément crucial pour le SEO."
    elif not 10 <= title_len <= 60:
        score, msg = 0.5, f"La longueur du titre ({title_len} car.) est sous-optimale. Visez entre 10 et 60 caractères."
    else:
        score, msg = 1, "La longueur du titre est excellente."
    checks.append(create_check("Title Tag", score, f"{title_len} caractères", msg, details=title_text))

    # 2. Meta Description
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc_tag['content'].strip() if desc_tag and 'content' in desc_tag.attrs else ""
    desc_len = len(desc_text)
    if not desc_text:
        score, msg = 0, "La balise meta description est absente. Elle est vitale pour le taux de clic."
    elif not 70 <= desc_len <= 160:
        score, msg = 0.5, f"La longueur de la description ({desc_len} car.) est sous-optimale. Visez entre 70 et 160 caractères."
    else:
        score, msg = 1, "La longueur de la description est parfaite."
    checks.append(create_check("Meta Description", score, f"{desc_len} caractères", msg, details=desc_text[:150]+"..."))

    # 3. Meta Viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport and 'content' in viewport.attrs:
        score, msg = 1, "La balise viewport est présente, assurant la compatibilité mobile."
        val = viewport['content']
    else:
        score, msg = 0, "La balise viewport est manquante. Le site ne sera pas responsive sur mobile."
        val = "Absente"
    checks.append(create_check("Meta Viewport", score, val, msg))

    # 4. URL Canonique
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    if canonical and 'href' in canonical.attrs:
        score, msg = 1, "Une URL canonique est définie, prévenant le contenu dupliqué."
        val = canonical['href']
    else:
        score, msg = 0.5, "L'URL canonique n'est pas définie. Risque de contenu dupliqué."
        val = "Absente"
    checks.append(create_check("URL Canonique", score, val, msg))

    return checks

def analyze_page_quality(soup: BeautifulSoup, html_content: str) -> List[Dict[str, Any]]:
    """Analyse la qualité et la structure du contenu visible."""
    checks = []
    text = soup.get_text(separator=' ')
    words = [w for w in re.findall(r'\b\w+\b', text.lower()) if len(w) > 1]
    word_count = len(words)

    checks.append(create_check("Nombre de Mots", 1 if word_count > 300 else 0.5, f"{word_count} mots", "Un contenu de plus de 300 mots est généralement mieux perçu."))

    html_size = len(html_content) / 1024
    text_size = len(text) / 1024
    ratio = (text_size / html_size * 100) if html_size > 0 else 0
    checks.append(create_check("Ratio Texte/HTML", 1 if ratio > 15 else 0.5, f"{ratio:.1f}%", "Un ratio élevé (>15%) indique un contenu riche par rapport au code."))

    strong_tags = len(soup.find_all(['strong', 'b']))
    checks.append(create_check("Bold and Strong Tags", 1 if strong_tags > 0 else 0.5, f"{strong_tags} balise(s)", "Utiliser <strong> ou <b> aide à mettre en évidence les mots-clés."))

    favicon = soup.find('link', rel=lambda r: r and 'icon' in r.lower())
    checks.append(create_check("Favicon", 1 if favicon else 0, "Présente" if favicon else "Absente", "Le favicon améliore l'identité visuelle du site."))
    
    return checks

def analyze_page_structure(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Vérifie la hiérarchie des titres et l'optimisation des images."""
    checks = []
    
    # H1 Heading
    h1_tags = soup.find_all('h1')
    if len(h1_tags) == 0:
        score, msg, val = 0, "Aucune balise <h1> trouvée. C'est un élément SEO majeur.", "0 trouvée"
    elif len(h1_tags) > 1:
        score, msg, val = 0.5, "Plusieurs balises <h1> trouvées. Il ne devrait y en avoir qu'une.", f"{len(h1_tags)} trouvées"
    else:
        score, msg, val = 1, "Une seule balise <h1> a été trouvée, c'est parfait.", h1_tags[0].get_text(strip=True)
    checks.append(create_check("H1 Heading", score, val, msg))

    # Heading Structure
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    heading_levels = [int(h.name[1]) for h in headings]
    structure_ok = all(heading_levels[i] <= heading_levels[i+1] for i in range(len(heading_levels)-1))
    details = {f"h{i}": heading_levels.count(i) for i in range(1, 7) if heading_levels.count(i) > 0}
    checks.append(create_check("Heading Structure", 1 if structure_ok else 0.5, f"{len(headings)} titres", "La hiérarchie des titres (H1 > H2 > H3...) doit être logique.", details=details))

    # Image SEO (Alt attributes)
    images = soup.find_all('img')
    if not images:
        checks.append(create_check("Image SEO", 1, "Aucune image", "Pas d'images à analyser."))
    else:
        missing_alt = sum(1 for i in images if not i.get('alt', '').strip())
        score = (len(images) - missing_alt) / len(images)
        checks.append(create_check("Image SEO", score, f"{len(images) - missing_alt}/{len(images)} avec 'alt'", "L'attribut 'alt' est crucial pour l'accessibilité et le SEO des images."))
    
    # Schema.org Markup
    schema = soup.find('script', attrs={'type': 'application/ld+json'})
    checks.append(create_check("Additional Markup (Schema)", 1 if schema else 0.5, "Présent" if schema else "Absent", "Le balisage Schema.org aide Google à comprendre le contenu de votre page."))
    
    return checks

def analyze_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """Analyse les liens internes, externes et leur qualité."""
    links = soup.find_all('a', href=True)
    internal, external = 0, 0
    base_hostname = urlparse(base_url).hostname

    for link in links:
        href = urljoin(base_url, link.get('href'))
        if urlparse(href).hostname == base_hostname:
            internal += 1
        elif urlparse(href).hostname:
            external += 1
            
    return [
        create_check("Internal Links", 1 if internal > 0 else 0.5, f"{internal} lien(s)", "Un bon maillage interne est essentiel."),
        create_check("External Links", 1, f"{external} lien(s)", "Les liens externes vers des sites de qualité renforcent la crédibilité.")
    ]

def analyze_server(final_url: str, redirects: List[Any]) -> List[Dict[str, Any]]:
    """Vérifie la configuration serveur et la sécurité (à partir des données déjà collectées)."""
    checks = []
    
    # HTTPS
    is_https = final_url.startswith('https://')
    checks.append(create_check("HTTPS", 1 if is_https else 0, "Activé" if is_https else "Non activé", "Le HTTPS est un standard de sécurité et un facteur de classement."))

    # HTTP Redirects
    if not redirects:
        score, msg = 1, "Aucune redirection. L'URL est directe et efficace."
    else:
        score, msg = 0.5, f"{len(redirects)} redirection(s) détectée(s), ce qui peut ralentir le chargement."
    checks.append(create_check("HTTP Redirects", score, f"{len(redirects)} redirection(s)", msg, details=[f"{r.status_code}: {r.url}" for r in redirects]))
    
    # Robots.txt (INFORMATIONNEL SEULEMENT)
    checks.append(create_check("Robots.txt", 0.5, "Vérification manuelle", "Ce fichier doit être vérifié manuellement à la racine de votre site (ex: site.com/robots.txt). Il indique aux robots ce qu'ils peuvent explorer."))
    
    return checks

def analyze_external(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Vérifications informationnelles pour les facteurs externes (à partir du HTML)."""
    # Backlinks (Placeholder)
    checks = [create_check("Backlinks", 0.5, "Analyse externe requise", "Utilisez un outil dédié (Ahrefs, SEMrush) pour évaluer les liens pointant vers votre site.")]
    
    # Social Networks
    social_links = [a['href'] for a in soup.find_all('a', href=re.compile(r'facebook\.com|twitter\.com|linkedin\.com|instagram\.com'))]
    checks.append(create_check("Social Networks", 1 if social_links else 0.5, f"{len(social_links)} profil(s) détecté(s)", "Les liens vers les réseaux sociaux renforcent l'entité de votre marque.", details=social_links))

    return checks

# --- FONCTION PRINCIPALE ---
def analyze_seo_page(url: str) -> Dict[str, Any]:
    """
    Étape 1: Télécharge les informations de l'URL.
    Étape 2: Lance les analyses sur les données collectées.
    """
    try:
        # --- ÉTAPE 1: TÉLÉCHARGEMENT (la seule requête réseau) ---
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Collecte de toutes les données nécessaires
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        redirects = response.history
        final_url = response.url # URL finale après d'éventuelles redirections

    except requests.RequestException as e:
        return {"error": f"Impossible de récupérer l'URL : {e}", "success": False}

    # --- ÉTAPE 2: ANALYSE (utilise uniquement les données ci-dessus) ---
    all_checks = {
        "Meta/title": analyze_meta_title(soup),
        "Page quality": analyze_page_quality(soup, html_content),
        "Page structure": analyze_page_structure(soup),
        "Links": analyze_links(soup, final_url),
        "Server": analyze_server(final_url, redirects),
        "External": analyze_external(soup),
    }

    # Calcul du score global
    total_score, total_checks = 0, 0
    for category in all_checks.values():
        for check in category:
            total_score += check['score']
            total_checks += 1
            
    final_score = (total_score / total_checks) * 100 if total_checks > 0 else 0

    return {
        "url": url,
        "success": True,
        "overall_score": int(final_score),
        "results": all_checks,
        "raw_html": html_content
    }