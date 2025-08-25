# analyze_lcp.py
import requests
import os
from dotenv import load_dotenv

# Charge les env vars pour la clé API optionnelle
load_dotenv()

def analyze_lcp_page(url: str, strategy: str = "mobile") -> dict:
    """
    Analyse le LCP (Largest Contentful Paint) via l'API PageSpeed Insights.
    
    :param url: URL de la page à analyser
    :param strategy: "mobile" ou "desktop"
    :return: Dict avec success, data (lcp, score, etc.) ou error
    """
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "strategy": strategy,
        "category": "performance"  # Focus sur perf pour LCP
    }
    
    # Ajoute la clé API si disponible dans .env
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        params["key"] = api_key
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()  # Lance exception si pas 200
        
        data = response.json()
        
        # Extrait LCP du JSON
        lcp_audit = data.get("lighthouseResult", {}).get("audits", {}).get("largest-contentful-paint")
        if not lcp_audit:
            return {
                "success": False,
                "error": "LCP non trouvé dans la réponse de PageSpeed Insights"
            }
        
        lcp_value = lcp_audit.get("numericValue")  # En ms, e.g. 2500.0
        lcp_unit = lcp_audit.get("numericUnit", "millisecond")
        
        # Score simple basé sur les guidelines Google
        if lcp_value < 2500:
            score = "Bon (rapide !)"
            score_value = 90  # Pour un score global si tu veux
        elif lcp_value < 4000:
            score = "Moyen (améliorable)"
            score_value = 50
        else:
            score = "Mauvais (optimise tes images, fontes ou scripts !)"
            score_value = 0
        
        return {
            "success": True,
            "data": {
                "url": url,
                "strategy": strategy,
                "lcp": f"{lcp_value} {lcp_unit}",
                "score": score,
                "score_value": score_value,  # Optionnel, pour intégration à un score global SEO
                "full_audit": lcp_audit  # Détails complets pour debug ou plus d'infos
            }
        }
    
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Erreur lors de l'appel API PSI: {str(e)} (vérifie ta connexion ou ajoute une clé API)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur inattendue lors de l'analyse LCP: {str(e)}"
        }