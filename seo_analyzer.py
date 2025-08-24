# seo_analyzer.py
import requests
import json
import re
from bs4 import BeautifulSoup, Comment
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

def create_check(title, score, value, message, details=None):
    """Crée une structure de vérification standard."""
    check = {"title": title, "score": score, "value": value, "message": message}
    if details:
        check["details"] = details
    return check

# --- Les fonctions d'analyse sont maintenant beaucoup plus riches ---

def check_structure(soup):
    """Vérifie la structure générale et la complexité du document HTML."""
    checks = []
    # Balises de base (inchangé)
    doctype = soup.doctype if hasattr(soup, 'doctype') and soup.doctype else None
    is_html5 = doctype and 'html' in str(doctype).lower()
    checks.append(create_check("DOCTYPE HTML5", 1 if is_html5 else 0, "Déclaré" if is_html5 else "Absent", "Le DOCTYPE HTML5 est essentiel."))
    lang = soup.html.get('lang')
    checks.append(create_check("Attribut Lang", 1 if lang else 0, lang or "Non défini", "L'attribut 'lang' aide à la compréhension par les moteurs de recherche."))
    
    # NOUVEAU: Balise <main> multiple
    main_tags = soup.find_all('main')
    main_score = 1 if len(main_tags) == 1 else 0
    checks.append(create_check("Balise <main> unique", main_score, f"{len(main_tags)} trouvée(s)", "Une page doit avoir une seule balise <main> pour le contenu principal."))
    
    # NOUVEAU: Complexité du DOM
    div_count = len(soup.find_all('div'))
    div_score = 1 if div_count < 150 else 0.5 if div_count < 300 else 0
    checks.append(create_check("Complexité (Divs)", div_score, f"{div_count} balises <div>", "Un grand nombre de divs peut indiquer une complexité inutile et ralentir le rendu."))

    # NOUVEAU: Commentaires HTML
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    comment_count = len(comments)
    checks.append(create_check("Commentaires HTML", 1, f"{comment_count} commentaire(s)", "Les commentaires doivent être supprimés en production pour alléger le fichier."))
    
    return checks

def check_head_tags(soup):
    """Vérifie les balises essentielles et les métadonnées dans le <head>."""
    # ... (Les vérifications Title, Meta Description, Canonical, Favicon restent les mêmes) ...
    # Pour la concision, je ne les répète pas ici, mais elles restent dans le code final.
    checks = []
    title = soup.find('title')
    title_text = title.get_text(strip=True) if title else ""
    title_len = len(title_text)
    title_score = 1 if 10 < title_len < 65 else 0.5 if title_text else 0
    checks.append(create_check("Balise Title", title_score, f"{title_text} ({title_len} chars)", "Le titre doit être unique et faire entre 10 et 65 caractères."))
    desc = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc.get('content', '').strip() if desc else ""
    desc_len = len(desc_text)
    desc_score = 1 if 70 < desc_len < 160 else 0.5 if desc_text else 0
    checks.append(create_check("Meta Description", desc_score, f"{desc_text[:100]}... ({desc_len} chars)", "La description doit être engageante et faire entre 70 et 160 caractères."))
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    checks.append(create_check("URL Canonique", 1 if canonical else 0.5, canonical.get('href') if canonical else "Non trouvée", "La balise canonique évite le contenu dupliqué."))
    favicon = soup.find('link', rel=lambda r: r and 'icon' in r)
    checks.append(create_check("Favicon", 1 if favicon else 0, "Trouvée" if favicon else "Non trouvée", "Le favicon améliore la reconnaissance de la marque."))
    return checks

def check_content_analysis(soup):
    """Analyse en profondeur le contenu textuel de la page."""
    checks = []
    text = soup.get_text(separator=' ')
    words = [w for w in re.findall(r'\b\w+\b', text.lower()) if len(w) > 1]
    word_count = len(words)
    
    # Word Count (inchangé)
    content_score = 1 if word_count > 300 else 0.5
    checks.append(create_check("Nombre de Mots", content_score, f"{word_count} mots", "Un contenu de plus de 300 mots est généralement mieux perçu."))

    # NOUVEAU: Densité de mots-clés
    meaningful_words = [w for w in words if w not in FRENCH_STOP_WORDS and len(w) > 2]
    word_freq = {}
    for word in meaningful_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    
    keyword_details = {kw: f"{(freq / word_count * 100):.2f}%" for kw, freq in top_keywords}
    checks.append(create_check("Densité Mots-Clés", 1, f"Top 5: {list(keyword_details.keys())}", "Vérifiez que les mots les plus fréquents correspondent au sujet.", details=keyword_details))

    # NOUVEAU: Mots-clés dans le premier paragraphe
    first_p_text = ""
    main_content = soup.main or soup.body
    first_p = main_content.find('p')
    if first_p:
        first_p_text = first_p.get_text().lower()
    
    keywords_in_first_p = [kw for kw, freq in top_keywords[:2] if kw in first_p_text]
    first_p_score = 1 if len(keywords_in_first_p) > 0 else 0.5
    checks.append(create_check("Mots-clés en intro", first_p_score, f"{len(keywords_in_first_p)}/2 trouvés", "Placer les mots-clés principaux dans les 100 premiers mots est un bon signal."))

    # NOUVEAU: Lisibilité (longueur des phrases)
    sentences = re.split(r'[.!?]+', soup.get_text())
    sentence_count = len([s for s in sentences if len(s.split()) > 2])
    avg_sentence_len = word_count / sentence_count if sentence_count > 0 else 0
    readability_score = 1 if avg_sentence_len < 20 else 0.5 if avg_sentence_len < 25 else 0
    checks.append(create_check("Lisibilité (Phrases)", readability_score, f"~{avg_sentence_len:.0f} mots/phrase", "Des phrases courtes (moins de 20 mots en moyenne) améliorent la lisibilité."))
    
    # NOUVEAU: Texte dans les balises fortes
    strong_em_text = " ".join([tag.get_text(strip=True) for tag in soup.find_all(['strong', 'em'])])
    checks.append(create_check("Texte en emphase", 1, f"{len(strong_em_text.split())} mots", "Vérifiez que les balises <strong>/<em> sont utilisées pour des mots importants.", details=strong_em_text[:200]))

    return checks

def check_images(soup):
    """Vérifie l'optimisation complète des images."""
    images = soup.find_all('img')
    img_count = len(images)
    if img_count == 0:
        return [create_check("Images", 1, "0 image", "Pas d'images à analyser.")]
    
    checks = []
    alt_missing = sum(1 for i in images if not i.has_attr('alt') or i['alt'].strip() == '')
    alt_score = (img_count - alt_missing) / img_count
    checks.append(create_check("Texte Alternatif (Alt)", alt_score, f"{img_count - alt_missing}/{img_count} ont un 'alt' non vide", "L'attribut 'alt' est crucial pour l'accessibilité et le SEO."))

    # NOUVEAU: Attributs Title sur les images
    title_count = sum(1 for i in images if i.has_attr('title') and i['title'].strip() != '')
    checks.append(create_check("Attribut Title", 1, f"{title_count}/{img_count} ont un 'title'", "L'attribut 'title' ajoute un contexte supplémentaire au survol."))

    # NOUVEAU: Extensions d'images
    ext_counts = {}
    for img in images:
        src = img.get('src', '').lower()
        ext = re.findall(r'\.(webp|jpg|jpeg|png|gif|svg)\b', src)
        if ext:
            ext_counts[ext[0]] = ext_counts.get(ext[0], 0) + 1
    webp_score = ext_counts.get('webp', 0) / img_count if img_count > 0 else 1
    checks.append(create_check("Format WebP", webp_score, f"{ext_counts.get('webp', 0)}/{img_count} sont en WebP", "Le format WebP offre une meilleure compression que le JPG/PNG.", details=ext_counts))

    # NOUVEAU: Images en Base64
    base64_count = sum(1 for i in images if i.get('src', '').strip().startswith('data:image'))
    base64_score = 0 if base64_count > 2 else 0.5 if base64_count > 0 else 1
    checks.append(create_check("Images Base64", base64_score, f"{base64_count} trouvée(s)", "Les images en Base64 peuvent ralentir le rendu HTML. À utiliser avec parcimonie."))

    return checks

def check_links(soup, base_url):
    """Analyse complète des liens."""
    checks = []
    links = soup.find_all('a', href=True)
    
    # ... (les compteurs internes/externes restent)
    internal, external = 0, 0
    social_links, contact_links = set(), set()
    rel_counts = {'nofollow': 0, 'sponsored': 0, 'ugc': 0}

    for link in links:
        href = link.get('href')
        if not href: continue

        # NOUVEAU: Détection liens tel/mailto
        if href.startswith('mailto:'):
            contact_links.add('Email')
        if href.startswith('tel:'):
            contact_links.add('Téléphone')

        # NOUVEAU: Scan des attributs rel
        rel = link.get('rel', [])
        for rel_type in rel_counts:
            if rel_type in rel:
                rel_counts[rel_type] += 1
        
        full_url = urljoin(base_url, href)
        hostname = urlparse(full_url).hostname
        
        if hostname == urlparse(base_url).hostname:
            internal += 1
        elif hostname:
            external += 1
            # NOUVEAU: Détection des liens sociaux
            if any(social in hostname for social in ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com']):
                social_links.add(hostname.split('.')[-2].capitalize())

    checks.append(create_check("Maillage (Liens internes)", 1, f"{internal} liens", "Un bon maillage interne aide à la navigation et au SEO."))
    checks.append(create_check("Liens Externes", 1, f"{external} liens", "Les liens externes doivent pointer vers des sources de qualité."))
    checks.append(create_check("Liens Sociaux", 1, f"{len(social_links)} profils trouvés", "Les liens vers les réseaux sociaux renforcent l'entité de la marque.", details=list(social_links)))
    checks.append(create_check("Liens de Contact", 1, f"{len(contact_links)} types trouvés", "Les liens mailto: et tel: facilitent la prise de contact sur mobile.", details=list(contact_links)))
    checks.append(create_check("Attributs 'rel'", 1, f"nofollow: {rel_counts['nofollow']}, sponsored: {rel_counts['sponsored']}", "L'utilisation correcte de nofollow/sponsored/ugc est importante pour Google.", details=rel_counts))
    return checks

def check_performance(html_content, soup):
    """Vérifie des points techniques liés à la performance."""
    checks = []
    # NOUVEAU: CSS/JS Inline
    inline_style_size = sum(len(s.string) for s in soup.find_all('style') if s.string)
    inline_script_size = sum(len(s.string) for s in soup.find_all('script') if not s.has_attr('src') and s.string)
    
    style_score = 1 if inline_style_size < 5000 else 0.5
    checks.append(create_check("CSS Inline", style_score, f"~{inline_style_size/1024:.1f} KB", "Le CSS critique peut être inline, mais les gros blocs devraient être dans des fichiers externes."))
    
    script_score = 1 if inline_script_size == 0 else 0.5
    checks.append(create_check("JS Inline", script_score, f"~{inline_script_size/1024:.1f} KB", "Le JS inline bloque le rendu. Il est préférable de le charger de manière asynchrone."))
    
    return checks

def analyze_seo_page(url: str) -> Dict[str, Any]:
    """Fonction principale d'analyse SEO complète - Édition Pablo."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
    except requests.RequestException as e:
        return {"error": f"Impossible de récupérer l'URL : {e}", "success": False}

    all_checks = {
        "structure": check_structure(soup),
        "head": check_head_tags(soup),
        "content": check_content_analysis(soup),
        "images": check_images(soup),
        "links": check_links(soup, url),
        "performance": check_performance(html_content, soup),
        # On peut ajouter ici les autres catégories comme social, technical etc.
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
        "results": all_checks
    }