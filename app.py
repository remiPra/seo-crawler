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

# ========== ENDPOINTS EXISTANTS (inchangés) ==========
@app.get("/health")
def health():
    return {"ok": True}



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