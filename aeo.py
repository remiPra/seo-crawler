# aeo.py - Module d'analyse AEO séparé
import requests
from bs4 import BeautifulSoup
import json
import re
import os
from typing import Dict, Any, List, Optional

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY", "")
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def analyze_aeo_page(url: str, use_ai: bool = True) -> Dict[str, Any]:
    """
    Analyse AEO complète d'une page selon la checklist 2025
    """
    try:
        # Scraping de base
        headers = {"User-Agent": "AEO-Analyzer/1.0 (+https://example.com/bot)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = f"{response.url.split('/')[0]}//{response.url.split('/')[2]}"
        
        # Initialisation
        score = 100
        issues = []
        found = {}
        
        # === 📂 FICHIERS IA ===
        aeo_files = _check_aeo_files(base_url, headers)
        for file_path, data in aeo_files.items():
            if data['exists']:
                score += 5
                found[f"file_{file_path[1:]}"] = True
            else:
                score -= 3
                issues.append(f"Fichier {file_path} manquant - opportunité AEO")
        
        # === 🏷️ MÉTADONNÉES IA ===
        ai_meta_score, ai_meta_found, ai_meta_issues = _analyze_ai_metadata(soup)
        score += ai_meta_score
        found.update(ai_meta_found)
        issues.extend(ai_meta_issues)
        
        # === 📐 STRUCTURE CONVERSATIONNELLE ===
        struct_score, struct_found, struct_issues = _analyze_conversational_structure(soup)
        score += struct_score
        found.update(struct_found)
        issues.extend(struct_issues)
        
        # === 📊 DONNÉES STRUCTURÉES ===
        schema_score, schema_found, schema_issues = _analyze_structured_data(soup)
        score += schema_score
        found.update(schema_found)
        issues.extend(schema_issues)
        
        # === 🏆 E-E-A-T SIGNALS ===
        eat_score, eat_found, eat_issues = _analyze_eat_signals(soup)
        score += eat_score
        found.update(eat_found)
        issues.extend(eat_issues)
        
        # === 🧪 OPTIMISATION CONTENU ===
        content_score, content_found, content_issues = _analyze_aeo_content(soup)
        score += content_score
        found.update(content_found)
        issues.extend(content_issues)
        
        # Score final
        final_score = max(0, min(100, score))
        
        # === 💡 RECOMMANDATIONS IA ===
        ai_recs = []
        if use_ai and HAS_OPENAI and openai.api_key:
            ai_recs = _get_ai_recommendations(url, final_score, found, issues[:3])
        else:
            ai_recs = _get_fallback_recommendations(found, issues)
        
        return {
            "url": url,
            "aeo_score": final_score,
            "grade": _get_aeo_grade(final_score),
            "analysis": {
                "files": aeo_files,
                "metadata": ai_meta_found,
                "structure": struct_found,
                "schema": schema_found,
                "eat": eat_found,
                "content": content_found
            },
            "issues": issues,
            "ai_recommendations": ai_recs,
            "quick_wins": _get_quick_wins(found, issues)
        }
        
    except Exception as e:
        return {"error": f"Analyse AEO échouée: {str(e)}", "url": url, "aeo_score": 0}

def _check_aeo_files(base_url: str, headers: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Vérifie les fichiers /llms.txt, /ai.txt, robots.txt"""
    files_to_check = ['/llms.txt', '/ai.txt', '/robots.txt']
    results = {}
    
    for file_path in files_to_check:
        try:
            resp = requests.get(base_url + file_path, headers=headers, timeout=5)
            results[file_path] = {
                "exists": resp.status_code == 200,
                "status": resp.status_code,
                "preview": resp.text[:150] if resp.status_code == 200 else None
            }
        except:
            results[file_path] = {"exists": False, "status": 0, "preview": None}
    
    return results

def _analyze_ai_metadata(soup) -> tuple:
    """Analyse des métadonnées IA spécialisées"""
    ai_metas = {
        'llm-friendly': 'Déclaration LLM-friendly',
        'ai-content-declaration': 'Déclaration contenu IA', 
        'content-summary': 'Résumé pour IA',
        'key-points': 'Points-clés structurés',
        'answer-engine-optimization': 'Mots-clés AEO'
    }
    
    score = 0
    found = {}
    issues = []
    
    for meta_name, description in ai_metas.items():
        meta_tag = soup.find('meta', attrs={'name': meta_name})
        if meta_tag and meta_tag.get('content'):
            found[f"meta_{meta_name.replace('-', '_')}"] = meta_tag.get('content')
            score += 6
        else:
            issues.append(f"Meta {meta_name} manquante ({description})")
            score -= 2
    
    return score, found, issues

def _analyze_conversational_structure(soup) -> tuple:
    """Structure optimisée pour recherche vocale"""
    score = 0
    found = {}
    issues = []
    
    # H1 unique
    h1s = soup.find_all('h1')
    if len(h1s) == 0:
        issues.append("❌ H1 manquant - CRITIQUE pour AEO")
        score -= 20
    elif len(h1s) > 1:
        issues.append(f"⚠️ {len(h1s)} H1 trouvés (1 recommandé pour AEO)")
        score -= 15
    else:
        found['h1_text'] = h1s[0].get_text(strip=True)
        score += 5
    
    # Questions naturelles dans H2/H3
    h2h3s = soup.find_all(['h2', 'h3'])
    question_words = ['comment', 'pourquoi', 'que', 'quoi', 'quand', 'où', 'quel']
    question_count = 0
    
    for heading in h2h3s:
        text = heading.get_text().lower()
        if any(word in text for word in question_words) or '?' in text:
            question_count += 1
    
    found['question_headings'] = question_count
    if question_count == 0 and len(h2h3s) > 0:
        issues.append("Aucun titre en question naturelle (recherche vocale)")
        score -= 8
    else:
        score += question_count * 3
    
    # Dates structurées
    time_elements = soup.find_all('time', datetime=True)
    found['structured_dates'] = len(time_elements)
    if len(time_elements) == 0:
        issues.append("Dates non structurées (<time datetime>)")
        score -= 5
    else:
        score += 3
    
    return score, found, issues

def _analyze_structured_data(soup) -> tuple:
    """Analyse Schema.org pour AEO"""
    score = 0
    found = {}
    issues = []
    
    json_lds = soup.find_all('script', type='application/ld+json')
    schema_types = []
    
    for script in json_lds:
        try:
            if script.string:
                data = json.loads(script.string)
                if isinstance(data, list):
                    schema_types.extend([item.get('@type') for item in data if isinstance(item, dict) and '@type' in item])
                elif isinstance(data, dict) and '@type' in data:
                    schema_types.append(data['@type'])
        except:
            continue
    
    # Schémas AEO-friendly
    aeo_schemas = ['FAQPage', 'HowTo', 'Article', 'Dataset', 'QAPage']
    found_aeo = [s for s in schema_types if s in aeo_schemas]
    
    found['schema_types'] = schema_types
    found['aeo_schemas'] = found_aeo
    
    if found_aeo:
        score += len(found_aeo) * 8
    else:
        issues.append("Aucun schema AEO (FAQPage, HowTo, Article)")
        score -= 5
    
    return score, found, issues

def _analyze_eat_signals(soup) -> tuple:
    """Signaux E-E-A-T pour crédibilité"""
    score = 0
    found = {}
    issues = []
    
    legal_keywords = ['privacy', 'mentions', 'legal', 'about', 'contact', 'terms']
    legal_found = []
    
    for link in soup.find_all('a', href=True):
        href_text = (link.get('href', '') + ' ' + link.get_text()).lower()
        for keyword in legal_keywords:
            if keyword in href_text and keyword not in legal_found:
                legal_found.append(keyword)
    
    found['eat_pages'] = legal_found
    eat_score = len(legal_found)
    
    if eat_score < 3:
        issues.append(f"Signaux E-A-T faibles ({eat_score}/6 pages légales)")
        score -= 10
    else:
        score += 5
    
    return score, found, issues

def _analyze_aeo_content(soup) -> tuple:
    """Contenu optimisé pour IA"""
    score = 0
    found = {}
    issues = []
    
    # Nombre de mots
    text_content = soup.get_text()
    word_count = len(re.findall(r'\b\w+\b', text_content))
    found['word_count'] = word_count
    
    if word_count < 300:
        issues.append(f"Contenu court ({word_count} mots) - insuffisant")
        score -= 8
    elif word_count > 1000:
        score += 5
    
    # FAQ détectée
    faq_selectors = [
        '[class*="faq" i]', '[id*="faq" i]', 
        '[class*="question" i]', '[class*="answer" i]'
    ]
    
    has_faq = any(soup.select(selector) for selector in faq_selectors)
    found['has_faq'] = has_faq
    
    if has_faq:
        score += 8
    else:
        issues.append("Section FAQ non détectée - crucial pour Answer Boxes")
        score -= 5
    
    return score, found, issues

def _get_ai_recommendations(url: str, score: int, found: Dict, issues: List[str]) -> List[str]:
    """Recommandations via OpenAI"""
    try:
        prompt = f"""Site analysé: {url}
Score AEO: {score}/100

Top problèmes:
{chr(10).join(f'- {issue}' for issue in issues)}

Donne 3 actions concrètes pour optimiser ce site pour Perplexity, ChatGPT et Google SGE.
Format court et actionnable."""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        
        text = response.choices[0].message.content.strip()
        return [rec.strip() for rec in text.split('\n') if rec.strip() and len(rec) > 10][:3]
        
    except Exception as e:
        return _get_fallback_recommendations(found, issues)

def _get_fallback_recommendations(found: Dict, issues: List[str]) -> List[str]:
    """Recommandations de secours sans OpenAI"""
    recs = []
    
    if "Dates non structurées" in str(issues):
        recs.append("Ajouter des dates structurées avec <time datetime='YYYY-MM-DD'>")
    
    if found.get('question_headings', 0) < 2:
        recs.append("Transformer 2-3 H2 en questions directes (Comment, Pourquoi, etc.)")
    
    if not found.get('aeo_schemas'):
        recs.append("Implémenter Schema FAQPage pour vos sections Q/R")
    
    if not found.get('file_ai_txt'):
        recs.append("Créer le fichier /ai.txt pour signaler votre contenu aux IA")
    
    return recs[:3] if recs else ["Optimiser le contenu pour l'AEO", "Structurer les données", "Améliorer E-A-T"]

def _get_aeo_grade(score: int) -> str:
    """Grade AEO basé sur le score"""
    if score >= 85: return "🟢 Excellent AEO"
    elif score >= 65: return "🟡 Bon AEO" 
    elif score >= 45: return "🟠 AEO Moyen"
    else: return "🔴 AEO Faible"

def _get_quick_wins(found: Dict, issues: List[str]) -> List[str]:
    """Actions rapides recommandées"""
    wins = []
    
    if not found.get('file_llms_txt'):
        wins.append("Créer /llms.txt avec vos 10 meilleures pages")
    
    if not found.get('aeo_schemas'):
        wins.append("Ajouter Schema FAQPage à votre contenu Q/R")
    
    if found.get('question_headings', 0) < 2:
        wins.append("Transformer 2-3 H2 en questions directes")
    
    if not found.get('meta_content_summary'):
        wins.append("Ajouter meta content-summary pour résumé IA")
    
    return wins[:3]