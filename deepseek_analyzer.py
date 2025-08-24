# deepseek_analyzer.py
import os
import requests
from openai import OpenAI
from bs4 import BeautifulSoup, Comment # Importation de Comment
from typing import Dict, Any, Optional
import json
from dotenv import load_dotenv

# Charge le fichier .env
load_dotenv()  

def get_html_content(url: str) -> Optional[str]:
    """Récupère le HTML complet d'une page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        print(f"✅ HTML récupéré ({len(response.text):,} caractères)")
        return response.text
        
    except Exception as e:
        print(f"❌ Erreur récupération HTML : {e}")
        return None

def check_ai_files(base_url: str) -> Dict[str, Any]:
    """Vérifie l'existence des fichiers IA (llms.txt, ai.txt, robots.txt)"""
    files_to_check = {
        'llms.txt': f"{base_url.rstrip('/')}/llms.txt",
        'ai.txt': f"{base_url.rstrip('/')}/ai.txt", 
        'robots.txt': f"{base_url.rstrip('/')}/robots.txt",
        'sitemap.xml': f"{base_url.rstrip('/')}/sitemap.xml"
    }
    
    results = {}
    
    for filename, file_url in files_to_check.items():
        try:
            response = requests.get(file_url, timeout=10)
            if response.status_code == 200:
                results[filename] = {
                    'exists': True,
                    'content_preview': response.text[:200] + "..." if len(response.text) > 200 else response.text
                }
                if filename == 'robots.txt':
                    ai_bots = ['GPTBot', 'PerplexityBot', 'Claude-Web', 'Google-Extended', 'CCBot']
                    bot_status = {}
                    for bot in ai_bots:
                        if bot in response.text:
                            if f"Disallow: /" in response.text and bot in response.text:
                                bot_status[bot] = 'BLOQUÉ'
                            else:
                                bot_status[bot] = 'AUTORISÉ'
                        else:
                            bot_status[bot] = 'NON MENTIONNÉ'
                    results[filename]['ai_bots'] = bot_status
            else:
                results[filename] = {'exists': False, 'status_code': response.status_code}
        except Exception as e:
            results[filename] = {'exists': False, 'error': str(e)}
    
    return results

def analyze_with_deepseek(html_content: str, ai_files_check: Dict[str, Any], url: str) -> Optional[str]:
    """Analyse complète d'optimisation IA avec DeepSeek V3, incluant nettoyage et troncature intelligente."""
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise Exception("DEEPSEEK_API_KEY non configurée dans les variables d'environnement")
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # --- SECTION DE NETTOYAGE ET TRONCATURE INTELLIGENTE ---

    # 1. Parser le HTML une seule fois avec BeautifulSoup
    print("🧹 Nettoyage du HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 2. Enlever les balises inutiles pour l'analyse de contenu (scripts, styles, svg)
    for element in soup(["script", "style", "svg"]):
        element.decompose()
        
    # 3. Enlever les commentaires HTML qui peuvent être longs et inutiles
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    # 4. Récupérer le HTML nettoyé. prettify() le rend plus lisible pour l'IA.
    cleaned_html = soup.prettify()
    print(f"🧼 HTML nettoyé, taille réduite à {len(cleaned_html):,} caractères.")

    # 5. Appliquer une troncature de sécurité sur le HTML *nettoyé* pour respecter la limite du modèle
    MAX_CHARS = 115000  # Limite de sécurité (32k tokens * ~3.5 chars/token)
    
    if len(cleaned_html) > MAX_CHARS:
        html_to_analyze = cleaned_html[:MAX_CHARS] + "\n\n<!-- NOTE POUR L'IA: Le contenu HTML a été nettoyé puis tronqué car il dépassait la taille maximale d'analyse. L'audit se base sur le début du document. -->"
        print(f"✂️  HTML tronqué à {MAX_CHARS} caractères car il restait trop volumineux.")
    else:
        html_to_analyze = cleaned_html

    # --- FIN DE LA SECTION DE NETTOYAGE ---
    
    # Extraire quelques infos clés pour le prompt à partir de l'objet 'soup' déjà créé
    title = soup.find('title')
    title_text = title.get_text().strip() if title else "Pas de titre"
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_desc_text = meta_desc.get('content', "Pas de meta description").strip()
    
    h1_tags = soup.find_all('h1')
    h1_count = len(h1_tags)
    h1_text = [h1.get_text(strip=True) for h1 in h1_tags]
    
    prompt = f"""
AUDIT SPÉCIALISÉ : OPTIMISATION POUR IA (Perplexity, ChatGPT, Claude, Gemini)
URL analysée : {url}

**DONNÉES PRÉLIMINAIRES :**
- Title: {title_text[:100]}...
- Meta description: {meta_desc_text[:100]}...  
- Nombre de H1: {h1_count}
- H1 trouvés: {h1_text}

**FICHIERS IA DÉTECTÉS :**
{json.dumps(ai_files_check, indent=2)}

**CHECKLIST COMPLÈTE À AUDITER :**

🔍 **SECTION 1: ACCÈS & FICHIERS IA**
- [ ] Présence /llms.txt à la racine
- [ ] Présence /ai.txt (optionnel)  
- [ ] robots.txt autorise GPTBot, PerplexityBot, Claude-Web, Google-Extended
- [ ] Sitemaps complets & à jour

🏷️ **SECTION 2: MÉTADONNÉES IA SPÉCIFIQUES**
Rechercher dans le HTML ces balises spéciales :
- [ ] <meta name="llm-friendly" content="true">
- [ ] <meta name="ai-content-declaration" content="human-generated">
- [ ] <meta name="content-summary" content="...">
- [ ] <meta name="key-points" content="...">
- [ ] <meta name="answer-engine-optimization" content="...">
- [ ] Balises <time datetime="..."> pour les dates

📐 **SECTION 3: STRUCTURATION CONTENU POUR IA**
- [ ] H1 unique = sujet clair (vérifier qu'il n'y en a qu'un)
- [ ] H2/H3 formulés en questions naturelles
- [ ] Réponse directe en première phrase des sections
- [ ] Paragraphes courts (2–4 phrases max)
- [ ] Listes à puces ou numérotées présentes
- [ ] Pas de "cela/ça" ambigu → références claires
- [ ] Balises sémantiques : <strong>, <em>, <cite>, <abbr>, <dfn>, <blockquote>
- [ ] FAQ intégrée visible

📊 **SECTION 4: DONNÉES STRUCTURÉES (Schema.org)**
Détecter dans le JSON-LD ou microdonnées :
- [ ] Organization / LocalBusiness avec NAP
- [ ] FAQPage pour Q/R
- [ ] HowTo pour tutoriels
- [ ] Article / BlogPosting (auteur, date, éditeur)
- [ ] Product / Offer si e-commerce
- [ ] Dataset / DigitalDocument si applicable

🏆 **SECTION 5: CRÉDIBILITÉ (E-E-A-T)**
- [ ] Auteur identifié + bio avec expertise
- [ ] Sources externes citées avec liens
- [ ] Avis clients / témoignages visibles
- [ ] Page À propos accessible
- [ ] Mentions légales + Contact
- [ ] sameAs dans JSON-LD (réseaux sociaux)

🧪 **SECTION 6: OPTIMISATION MOTEURS DE RÉPONSE**
- [ ] Contenu adapté recherche vocale
- [ ] Snippets réutilisables (phrases percutantes)
- [ ] Réponses autonomes par section
- [ ] Maillage interne FAQ/guides
- [ ] Dates de mise à jour visibles

**FORMAT DE RÉPONSE DEMANDÉ :**

Pour chaque section, donne :
✅ = Critère respecté (avec exemple du HTML)
⚠️ = Partiellement respecté (avec détails)
❌ = Non respecté ou absent

**SCORE FINAL :**
- Score optimisation IA : X/100
- Top 3 des points forts pour les IA
- Top 5 des améliorations prioritaires pour être mieux référencé par Perplexity/ChatGPT/Claude

HTML à analyser (nettoyé et potentiellement tronqué) :
{html_to_analyze}
"""
    
    try:
        print("🤖 DeepSeek V3 analyse l'optimisation IA...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096 # Augmenté légèrement pour des rapports plus détaillés si besoin
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse DeepSeek : {e}")
        raise Exception(f"Erreur DeepSeek API: {str(e)}")

def analyze_ai_optimization_complete(url: str) -> Dict[str, Any]:
    """Fonction principale d'analyse complète"""
    try:
        base_url = '/'.join(url.split('/')[:3])
        ai_files_check = check_ai_files(base_url)
        
        html_content = get_html_content(url)
        
        if not html_content:
            return {
                "url": url,
                "error": "Impossible de récupérer le HTML de la page",
                "success": False
            }
        
        ai_report = analyze_with_deepseek(html_content, ai_files_check, url)
        
        return {
            "url": url,
            "success": True,
            "ai_files_check": ai_files_check,
            "html_size": len(html_content),
            "deepseek_analysis": ai_report,
            "model_used": "deepseek-chat",
            "analysis_type": "AI Optimization Audit"
        }
        
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "success": False
        }