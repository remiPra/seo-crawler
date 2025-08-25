# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
import edge_tts
import io
from seo_crawler import crawl as crawl_bs
from deepseek_analyzer import analyze_ai_optimization_complete

# Import AEO
from aeo import analyze_aeo_page
from seo_analyzer import analyze_seo_page
from analyze_lcp import analyze_lcp_page  # Assure-toi que c'est async
# Imports pour le nouveau endpoint LCP
import requests
from dotenv import load_dotenv
import os

# Charge les env vars (pour clé API PSI optionnelle)
load_dotenv()

# Playwright en option si tu en as besoin (inchangé)
async def crawl_js_lazy(url: str, max_pages: int):
    from seo_crawler_js import crawl_js
    return await crawl_js(url, max_pages)

app = FastAPI(title="SEO Tool (Rules + Scores) + TTS + AEO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# ========== MODÈLES EXISTANTS ==========
class Body(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 60
    js: Optional[bool] = False

# --- NOUVEAU MODÈLE Pydantic ---
class SEORequest(BaseModel):
    url: HttpUrl

# Nouveau modèle pour Playwright
class PlaywrightTestRequest(BaseModel):
    url: Optional[HttpUrl] = "https://httpbin.org/json"
    action: Optional[str] = "basic"  # "basic", "screenshot", "content"




class SynthesizeRequest(BaseModel):
    text: str
    voice: Optional[str] = "fr-FR-DeniseNeural"

# ========== NOUVEAU MODÈlE DEEPSEEK ==========
class DeepSeekAIRequest(BaseModel):
    url: HttpUrl

# ========== NOUVEAU MODÈLE AEO ==========
class AEORequest(BaseModel):
    url: HttpUrl
    use_ai_recommendations: Optional[bool] = True

# ========== NOUVEAU MODÈLE POUR LCP ==========
class LCPRequest(BaseModel):
    url: HttpUrl
    strategy: Optional[str] = "mobile"  # "mobile" ou "desktop"

@app.post("/test-playwright")
async def test_playwright(request: PlaywrightTestRequest):
    """
    🎭 Test Playwright - Vérifiez que tout fonctionne parfaitement !
    
    Actions disponibles:
    - basic: Test simple avec infos de la page
    - screenshot: Capture d'écran en base64
    - content: Extraction de contenu complet
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.newPage()
            
            # Navigation
            await page.goto(str(request.url), wait_until="networkidle")
            
            result = {
                "success": True,
                "url": str(request.url),
                "action": request.action,
                "playwright_status": "✅ Fonctionne parfaitement !"
            }
            
            if request.action == "basic":
                result.update({
                    "title": await page.title(),
                    "viewport": page.viewport_size,
                    "user_agent": await page.evaluate("navigator.userAgent")
                })
                
            elif request.action == "screenshot":
                screenshot = await page.screenshot(type="png", full_page=True)
                result["screenshot_base64"] = base64.b64encode(screenshot).decode()
                result["screenshot_size"] = len(screenshot)
                
            elif request.action == "content":
                result.update({
                    "title": await page.title(),
                    "html_length": len(await page.content()),
                    "links_count": len(await page.locator("a").all()),
                    "images_count": len(await page.locator("img").all())
                })
            
            await browser.close()
            return result
            
    except Exception as e:
        raise HTTPException(500, f"Erreur Playwright: {str(e)}")




# ========== ENDPOINTS EXISTANTS (inchangés) ==========
@app.get("/health")
def health():
    return {"ok": True}

# --- NOUVEL ENDPOINT SEO ---
@app.post("/analyze-seo")
async def analyze_seo(request: SEORequest):
    """
    🚀 Analyse SEO technique complète d'une page
    
    Audit basé sur plus de 20 points de contrôle (structure, metas, contenu, images, etc.)
    """
    try:
        result = analyze_seo_page(str(request.url))
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "Erreur lors de l'analyse SEO"))
        return result
    except Exception as e:
        # Cette capture est plus générale pour les erreurs inattendues
        raise HTTPException(500, f"Erreur interne du serveur lors de l'analyse SEO: {str(e)}")

# ========== NOUVEL ENDPOINT DEEPSEEK ==========
@app.post("/analyze-ai-deepseek")
async def analyze_ai_deepseek(request: DeepSeekAIRequest):
    """
    🤖 Analyse optimisation IA avec DeepSeek V3
    
    Audit complet pour optimiser votre site pour :
    - Perplexity AI
    - ChatGPT / OpenAI
    - Claude / Anthropic  
    - Google SGE (Search Generative Experience)
    - Autres moteurs de réponse IA
    """
    try:
        result = analyze_ai_optimization_complete(str(request.url))
        
        if not result.get("success"):
            raise HTTPException(500, result.get("error", "Erreur inconnue"))
            
        return result
        
    except Exception as e:
        raise HTTPException(500, f"Erreur analyse DeepSeek: {str(e)}")

@app.post("/crawl")
async def crawl(body: Body):
    try:
        max_pages = max(1, min(body.max_pages or 60, 200))
        if body.js:
            data = await crawl_js_lazy(str(body.url), max_pages)
        else:
            data = crawl_bs(str(body.url), max_pages=max_pages)

        # trie: pires d'abord (score_global croissant)
        data_sorted = sorted(data, key=lambda x: x.get("score_global", x.get("score_legacy", 0)))
        return {"pages": len(data_sorted), "data": data_sorted}
    except Exception as e:
        raise HTTPException(500, str(e))

# ========== ENDPOINTS TTS ==========
@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthèse vocale avec Edge TTS - Compatible avec votre assistant vocal
    """
    try:
        text = request.text
        voice = request.voice or "fr-FR-DeniseNeural"
        
        if not text:
            raise HTTPException(400, "Texte manquant")
        
        if len(text) > 1000:
            raise HTTPException(400, "Texte trop long (max 1000 caractères)")
        
        # Génération avec Edge TTS
        communicate = edge_tts.Communicate(text, voice)
        
        # Collecte des chunks audio en mémoire
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        
        return StreamingResponse(
            io.BytesIO(audio_data.getvalue()),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        raise HTTPException(500, f"Échec de la synthèse vocale: {str(e)}")

@app.post("/synthesizeenglish") 
async def synthesize_english(request: SynthesizeRequest):
    """
    Synthèse vocale anglaise
    """
    try:
        # Force la voix anglaise
        english_request = SynthesizeRequest(
            text=request.text, 
            voice="en-US-AriaNeural"
        )
        return await synthesize(english_request)
        
    except Exception as e:
        raise HTTPException(500, f"Erreur synthèse anglaise: {str(e)}")

@app.get("/tts/voices")
async def get_voices():
    """
    Liste les voix disponibles Edge TTS
    """
    try:
        voices = await edge_tts.list_voices()
        # Filtrer les voix françaises + populaires
        french_voices = [
            {"name": v["Name"], "short_name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
            for v in voices if v["Locale"].startswith("fr") or v["Locale"].startswith("en-US")
        ]
        return {"voices": french_voices}
    except Exception as e:
        raise HTTPException(500, f"Erreur récupération voix: {str(e)}")

# ========== NOUVEL ENDPOINT AEO ==========
@app.post("/analyze-aeo")
async def analyze_aeo(request: AEORequest):
    """
    Analyse AEO (Answer Engine Optimization) - SEO pour l'ère de l'IA
    Optimise pour Perplexity, ChatGPT, Claude, Google SGE
    """
    try:
        result = analyze_aeo_page(str(request.url), request.use_ai_recommendations)
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur analyse AEO: {str(e)}")

# # ========== NOUVEL ENDPOINT LCP ==========
# @app.post("/analyze-lcp")
# async def analyze_lcp(request: LCPRequest):
#     """
#     ⚡ Analyse LCP (Largest Contentful Paint) via PageSpeed Insights
    
#     Vérifie un Core Web Vital clé pour la perf SEO (mobile/desktop).
#     Retourne la valeur en ms + un score simple.
#     """
#     try:
#         result = analyze_lcp_page(str(request.url), request.strategy)


# ========== NOUVEL ENDPOINT LCP (ajouté ici) ==========
# ========== NOUVEL ENDPOINT LCP ==========
@app.post("/analyze-lcp")
async def analyze_lcp(request: LCPRequest):
    """
    ⚡ Analyse LCP (Largest Contentful Paint) via scraping PageSpeed Insights
    
    Utilise Playwright pour charger et parser le rapport (attente ~30s).
    Retourne la valeur + score simple.
    """
    try:
        result = await analyze_lcp_page(str(request.url), request.strategy)
        
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "Erreur lors de l'analyse LCP"))
        
        return result
    except Exception as e:
        raise HTTPException(500, f"Erreur interne lors de l'analyse LCP: {str(e)}")
    """
    ⚡ Analyse LCP (Largest Contentful Paint) via PageSpeed Insights
    
    Vérifie un Core Web Vital clé pour la perf SEO (mobile/desktop).
    Retourne la valeur en ms + un score simple.
    """
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": str(request.url),
        "strategy": request.strategy,  # mobile ou desktop
        "category": "performance"  # Focus sur perf
    }
    
    # Ajoute la clé API si dispo dans .env
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        params["key"] = api_key
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extrait LCP
        lcp_audit = data.get("lighthouseResult", {}).get("audits", {}).get("largest-contentful-paint")
        if not lcp_audit:
            raise ValueError("LCP non trouvé dans la réponse PSI")
        
        lcp_value = lcp_audit.get("numericValue")  # En ms
        lcp_unit = lcp_audit.get("numericUnit", "millisecond")
        
        # Score simple
        if lcp_value < 2500:
            score = "Bon (rapide !)"
        elif lcp_value < 4000:
            score = "Moyen (améliorable)"
        else:
            score = "Mauvais (optimise tes images/fontes !)"
        
        return {
            "url": str(request.url),
            "strategy": request.strategy,
            "lcp": f"{lcp_value} {lcp_unit}",
            "score": score,
            "full_data": lcp_audit  # Détails optionnels
        }
    
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erreur API PSI: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne lors de l'analyse LCP: {str(e)}")
