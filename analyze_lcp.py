# analyze_lcp.py
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import quote  # Pour encoder l'URL

async def analyze_lcp_page(url: str, strategy: str = "mobile") -> dict:
    """
    Analyse le LCP via scraping de PageSpeed Insights avec Playwright + BeautifulSoup.
    
    :param url: URL de la page à analyser (e.g. "https://www.tamboursdelaterre.com/...")
    :param strategy: "mobile" ou "desktop"
    :return: Dict avec success, data (lcp, score, etc.) ou error
    """
    # Construit l'URL PSI (encode l'URL du site pour éviter les bugs)
    encoded_url = quote(url, safe='')
    form_factor = "mobile" if strategy == "mobile" else "desktop"
    psi_url = f"https://pagespeed.web.dev/analysis/{encoded_url}?form_factor={form_factor}&use_original_url=true"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Headless pour pas de fenêtre
            page = await browser.new_page()
            
            # Navigue et attend 30s que le rapport charge (JS async)
            await page.goto(psi_url)
            await page.wait_for_timeout(30000)  # 30 secondes, ajuste si besoin (plus long pour sites lents)
            
            # Récupère le HTML rendu
            html = await page.content()
            await browser.close()
            
            # Parse avec BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Trouve la section LCP (selector basé sur structure PSI typique)
            lcp_section = soup.find('div', class_='lh-metric', string=lambda text: 'Largest Contentful Paint' in text if text else False)
            if not lcp_section:
                # Alternative si le string ne matche pas : cherche par titre exact
                lcp_section = soup.find(lambda tag: tag.name == 'h3' and 'Largest Contentful Paint' in tag.text)
                if lcp_section:
                    lcp_section = lcp_section.find_parent('div', class_='lh-metric')
            
            if not lcp_section:
                return {
                    "success": False,
                    "error": "Section LCP non trouvée dans le rapport PSI (vérifie l'URL ou le selector)"
                }
            
            # Extrait la valeur (e.g. "2.5 s")
            lcp_value_tag = lcp_section.find('div', class_='lh-metric__value') or lcp_section.find('span', class_='lh-metric__innerwrap')
            lcp_value = lcp_value_tag.text.strip() if lcp_value_tag else "Inconnu"
            
            # Extrait un score basique (basé sur la class : pass=bon, average=moyen, fail=mauvais)
            score_class = lcp_section.get('class', [])
            if 'lh-metric--pass' in score_class:
                score = "Bon (rapide !)"
                score_value = 90
            elif 'lh-metric--average' in score_class:
                score = "Moyen (améliorable)"
                score_value = 50
            elif 'lh-metric--fail' in score_class:
                score = "Mauvais (optimise tes images/fontes !)"
                score_value = 0
            else:
                score = "Inconnu"
                score_value = 0
            
            return {
                "success": True,
                "data": {
                    "url": url,
                    "strategy": strategy,
                    "lcp": lcp_value,
                    "score": score,
                    "score_value": score_value,
                    "psi_url": psi_url  # Pour debug
                }
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors du scraping PSI avec Playwright: {str(e)} (vérifie Playwright installé et headless=True)"
        }

# Pour tester standalone (lance python analyze_lcp.py)
if __name__ == "__main__":
    test_url = "https://www.tamboursdelaterre.com/cranes-en-pierre-lise-meraud"
    result = asyncio.run(analyze_lcp_page(test_url))
    print(result)