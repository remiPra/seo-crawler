# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
from seo_crawler import crawl as crawl_bs

# Playwright est optionnel : on l'importe au runtime seulement si demandé
async def crawl_js_lazy(url: str, max_pages: int):
    from seo_crawler_js import crawl_js
    return await crawl_js(url, max_pages)

app = FastAPI(title="SEO Tool (BS4 + Playwright option)")

# CORS pour appeler depuis un front (Next.js, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

class Body(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 60
    js: Optional[bool] = False

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/crawl")
async def crawl(body: Body):
    try:
        max_pages = max(1, min(body.max_pages or 60, 200))
        if body.js:
            data = await crawl_js_lazy(str(body.url), max_pages)
        else:
            data = crawl_bs(str(body.url), max_pages=max_pages)
        return {"pages": len(data), "data": data}
    except Exception as e:
        raise HTTPException(500, str(e))
