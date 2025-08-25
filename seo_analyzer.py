# seo_analyzer.py
import requests
import re
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List

# --- FONCTION UTILITAIRE ---
def create_check(title: str, score: float, value: Any, message: str, details: Any = None) -> Dict[str, Any]:
    check = {"title": title, "score": score, "value": value, "message": message}
    if details:
        check["details"] = details
    return check

# --- FONCTIONS D'ANALYSE ---

def analyze_meta_title(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    checks = []
    # Balise Title (existant)
    title_tag = soup.find('title')
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    title_len = len(title_text)
    if not title_text: score, msg = 0, "La balise <title> est manquante."
    elif not 10 <= title_len <= 60: score, msg = 0.5, "La longueur du titre est sous-optimale (visez 10-60 car.)."
    else: score, msg = 1, "La longueur du titre est excellente."
    checks.append(create_check("Title Tag", score, f"{title_len} car.", msg))

    # Meta Description (existant)
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc_tag['content'].strip() if desc_tag and 'content' in desc_tag.attrs else ""
    desc_len = len(desc_text)
    if not desc_text: score, msg = 0, "La meta description est absente."
    elif not 70 <= desc_len <= 160: score, msg = 0.5, "La longueur de la description est sous-optimale (visez 70-160 car.)."
    else: score, msg = 1, "La longueur de la description est parfaite."
    checks.append(create_check("Meta Description", score, f"{desc_len} car.", msg))

    # NOUVEAU: Open Graph Metas
    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
    og_needed = ['og:title', 'og:type', 'og:image', 'og:url']
    og_found = [tag.get('property') for tag in og_tags]
    missing_og = [tag for tag in og_needed if tag not in og_found]
    score = 1 if len(og_tags) >= 4 and not missing_og else 0.5
    checks.append(create_check("Open Graph Metas", score, f"{len(og_tags)} balise(s)", "Essentiel pour un bon affichage sur Facebook, LinkedIn, etc.", details={"Présentes": og_found, "Manquantes (recommandées)": missing_og}))

    # NOUVEAU: Twitter Cards
    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
    score = 1 if len(twitter_tags) >= 2 else 0.5
    checks.append(create_check("Twitter Cards", score, f"{len(twitter_tags)} balise(s)", "Optimise les partages de votre page sur X (Twitter).", details=[t.get('name') for t in twitter_tags]))
    
    return checks

def analyze_page_quality(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    checks = []
    text = soup.get_text(separator=' ')
    words = [w for w in re.findall(r'\b\w+\b', text.lower()) if len(w) > 1 and w.isalpha()]
    word_count = len(words)
    sentences = [s for s in re.split(r'[.!?]+', text) if len(s.split()) > 2]
    sentence_count = len(sentences)

    checks.append(create_check("Nombre de Mots", 1 if word_count > 300 else 0.5, f"{word_count} mots", "Un contenu de plus de 300 mots est généralement mieux perçu."))

    # NOUVEAU: Densité de Mots-clés (heuristique basée sur le titre)
    title_words = set(re.findall(r'\b\w{4,}\b', soup.title.get_text(strip=True).lower()))
    if title_words:
        main_keyword = max(title_words, key=len)
        keyword_count = words.count(main_keyword)
        density = (keyword_count / word_count * 100) if word_count > 0 else 0
        score = 1 if 0.5 <= density <= 2.5 else 0.5
        val = f"{density:.2f}% pour '{main_keyword}'"
        msg = f"La densité idéale pour un mot-clé est entre 1% et 2%. Le mot-clé '{main_keyword}' a été extrait du titre."
    else:
        score, val, msg = 0.5, "N/A", "Impossible de déterminer un mot-clé principal depuis le titre."
    checks.append(create_check("Densité de Mots-clés", score, val, msg))

    # NOUVEAU: Score de Lisibilité (simple)
    if word_count > 0 and sentence_count > 0:
        avg_sentence_len = word_count / sentence_count
        score = 1 if avg_sentence_len < 20 else 0.5
        val = f"~{avg_sentence_len:.0f} mots/phrase"
        msg = "Des phrases courtes (< 20 mots) améliorent la lisibilité. Google apprécie les contenus clairs."
    else:
        score, val, msg = 0.5, "N/A", "Pas assez de contenu pour analyser la lisibilité."
    checks.append(create_check("Score de Lisibilité", score, val, msg))

    return checks

def analyze_page_structure(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    checks = []
    
    # H1 Heading (existant)
    h1s = soup.find_all('h1')
    if len(h1s) != 1: score, val = 0.5, f"{len(h1s)} trouvée(s)"
    else: score, val = 1, "1 trouvée"
    checks.append(create_check("H1 Heading", score, val, "Une page doit avoir une et une seule balise <h1>."))

    # Heading Structure (existant)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
    levels = [int(h.name[1]) for h in headings]
    structure_ok = all(levels[i] <= levels[i+1] or levels[i+1] <= levels[i] for i in range(len(levels)-1))
    checks.append(create_check("Hiérarchie des Titres", 1 if structure_ok else 0.5, "OK" if structure_ok else "Non logique", "La hiérarchie des titres (H1 > H2 > H3) doit être respectée."))

    # NOUVEAU: Balises Sémantiques
    semantic_tags = soup.find_all(['article', 'section', 'nav', 'header', 'footer', 'aside'])
    score = 1 if len(semantic_tags) >= 3 else 0.5
    checks.append(create_check("Balises Sémantiques", score, f"{len(semantic_tags)} trouvée(s)", "L'utilisation de <article>, <nav>, etc., aide les moteurs à comprendre la structure de la page.", details=[t.name for t in semantic_tags]))
    
    # NOUVEAU: Attributs ARIA
    interactive_elements = soup.find_all(['a', 'button', 'input'])
    aria_elements = [el for el in interactive_elements if el.has_attr('aria-label') or el.has_attr('aria-labelledby')]
    score = 1 if len(aria_elements) > 0 else 0.5
    checks.append(create_check("Attributs ARIA", score, f"{len(aria_elements)}/{len(interactive_elements)} éléments", "Les attributs ARIA améliorent l'accessibilité, un signal positif pour Google."))

    return checks

def analyze_links(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    checks = []
    links = soup.find_all('a', href=True)
    base_hostname = urlparse(base_url).hostname
    internal, external = 0, 0
    nofollow_external = 0
    generic_anchors = 0
    
    for link in links:
        href = urljoin(base_url, link.get('href'))
        is_external = urlparse(href).hostname != base_hostname and urlparse(href).hostname is not None
        
        if is_external:
            external += 1
            if 'nofollow' in link.get('rel', []):
                nofollow_external += 1
        else:
            internal += 1

        if link.get_text(strip=True).lower() in ["cliquez ici", "en savoir plus", "lire la suite", "ici"]:
            generic_anchors += 1

    checks.append(create_check("Liens Internes & Externes", 1, f"{internal} internes, {external} externes", "Un bon équilibre entre liens internes et externes est essentiel."))

    # NOUVEAU: Qualité des ancres
    score = 1 if generic_anchors == 0 else 0.5
    checks.append(create_check("Qualité des Ancres de Liens", score, f"{generic_anchors} ancre(s) générique(s)", "Évitez les textes d'ancre génériques comme 'cliquez ici'. Utilisez des mots-clés pertinents."))

    # NOUVEAU: Nofollow sur liens externes
    score = 1 if external == 0 or nofollow_external > 0 else 0.5
    checks.append(create_check("Nofollow sur Liens Externes", score, f"{nofollow_external}/{external} avec 'nofollow'", "Utilisez 'nofollow' pour les liens externes non fiables ou sponsorisés pour conserver votre 'jus SEO'."))

    return checks

def analyze_performance_basics(soup: BeautifulSoup, html_content: str) -> List[Dict[str, Any]]:
    """NOUVELLE CATÉGORIE pour la performance, basée sur le HTML."""
    checks = []
    
    # NOUVEAU: Optimisation des Images
    images = soup.find_all('img')
    missing_dims = sum(1 for img in images if not img.has_attr('width') or not img.has_attr('height'))
    lazy_loading = sum(1 for img in images if img.get('loading') == 'lazy')
    score = 1 if missing_dims == 0 else 0.5
    checks.append(create_check("Optimisation des Images", score, f"{len(images) - missing_dims}/{len(images)} avec dimensions", "Les attributs width/height sur les images empêchent les sauts de page (Layout Shift). 'loading=lazy' est un plus.", details=f"{lazy_loading} images avec lazy-loading"))

    # NOUVEAU: Minification du HTML
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    score = 1 if len(comments) == 0 else 0.5
    checks.append(create_check("Minification du HTML", score, f"{len(comments)} commentaire(s)", "Supprimez les commentaires HTML en production pour alléger le poids de la page."))
    
    # NOUVEAU: Taille du CSS/JS Inline
    inline_style_size = sum(len(s.string) for s in soup.find_all('style') if s.string)
    inline_script_size = sum(len(s.string) for s in soup.find_all('script') if not s.has_attr('src') and s.string)
    total_inline_kb = (inline_style_size + inline_script_size) / 1024
    score = 1 if total_inline_kb < 15 else 0.5
    checks.append(create_check("CSS/JS Inline", score, f"~{total_inline_kb:.1f} KB", "Un excès de CSS ou JS inline peut ralentir le premier rendu de la page. Visez moins de 15KB."))
    
    return checks

def analyze_server_and_external(soup: BeautifulSoup, final_url: str, redirects: List[Any]) -> List[Dict[str, Any]]:
    """Catégorie pour les vérifications serveur (light) et externes (info)."""
    checks = []
    checks.append(create_check("HTTPS", 1 if final_url.startswith('https://') else 0, "Activé" if final_url.startswith('https://') else "Non", "Le HTTPS est un standard de sécurité obligatoire."))
    checks.append(create_check("HTTP Redirects", 1 if not redirects else 0.5, f"{len(redirects)} redirection(s)", "Moins il y a de redirections, plus le chargement est rapide."))
    
    # NOUVEAU: Lien Sitemap (Info)
    sitemap_link = soup.find('a', href=re.compile(r'sitemap\.xml'))
    checks.append(create_check("Lien Sitemap", 1 if sitemap_link else 0.5, "Trouvé" if sitemap_link else "Non trouvé", "Un lien vers le sitemap.xml aide les moteurs de recherche à découvrir toutes vos pages."))

    # Facteurs externes (Info)
    checks.append(create_check("Backlinks", 0.5, "Analyse externe requise", "Utilisez un outil dédié (Ahrefs, SEMrush) pour évaluer les liens pointant vers votre site."))
    social_links = [a['href'] for a in soup.find_all('a', href=re.compile(r'facebook\.com|twitter\.com|linkedin\.com'))]
    checks.append(create_check("Présence Sociale", 1 if social_links else 0.5, f"{len(social_links)} profil(s) détecté(s)", "Les liens vers les réseaux sociaux renforcent votre marque."))

    return checks

# --- FONCTION PRINCIPALE ---
def analyze_seo_page(url: str) -> Dict[str, Any]:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        redirects = response.history
        final_url = response.url
    except requests.RequestException as e:
        return {"error": f"Impossible de récupérer l'URL : {e}", "success": False}

    all_checks = {
        "🎯 Meta & Titre": analyze_meta_title(soup),
        "⭐ Qualité de la Page": analyze_page_quality(soup),
        "🏗️ Structure de la Page": analyze_page_structure(soup),
        "🔗 Liens": analyze_links(soup, final_url),
        "🚀 Performance de Base": analyze_performance_basics(soup, html_content),
        "🖥️ Serveur & Externe": analyze_server_and_external(soup, final_url, redirects),
    }

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