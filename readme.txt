curl -X POST "http://localhost:8000/crawl" -H "Content-Type: application/json" -d '{"url": "https://www.monicamariage.com", "max_pages": 3}'
curl -X POST localhost:8000/crawl -H "Content-Type: application/json" -d '{"url":"https://www.monicamariage.com","max_pages":1}'

uvicorn app:app --reload
Tu as raison ! Je vais te faire une documentation claire et complète. Voici un **README.md** proper :

```markdown
# 🔍 SEO Audit Tool

Un outil d'audit SEO complet qui crawle et analyse automatiquement les sites web selon 30+ règles SEO modernes (2025).

## ✨ Fonctionnalités

- **Crawling automatique** : Découvre et analyse toutes les pages d'un site
- **Score SEO global** : Note de 0 à 100 avec détail par page
- **30+ règles SEO** : Meta tags, structure HTML, accessibilité, performance, sécurité
- **Recommandations détaillées** : Conseils précis pour améliorer le référencement
- **Support JavaScript** : Crawler Playwright en option pour les sites SPA
- **API REST** : Intégration facile dans d'autres outils

## 🚀 Installation & Lancement

### 1. Prérequis
```bash
# Python 3.8+ requis
pip install -r requirements.txt
```

### 2. Lancer l'API
```bash
# Lancement local
uvicorn app:app --reload

# L'API sera accessible sur : http://localhost:8000
```

### 3. Test rapide avec l'interface
Ouvre `test.html` dans ton navigateur, puis :
- Entre une URL (ex: `https://example.com`)
- Clique sur "Analyser"
- Regarde les résultats !

## 📡 Utilisation de l'API

### Endpoint principal : `POST /crawl`

**URL :** `http://localhost:8000/crawl`

**Paramètres :**
```json
{
  "url": "https://example.com",     // URL à analyser (obligatoire)
  "max_pages": 60,                 // Nombre max de pages (1-200, défaut: 60)
  "js": false                      // Utiliser Playwright pour le JS (défaut: false)
}
```

### Exemples d'utilisation

#### Curl basique (3 pages max)
```bash
curl -X POST localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","max_pages":3}'
```

#### Analyse complète (60 pages)
```bash
curl -X POST localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url":"https://monsite.com","max_pages":60}'
```

#### Site avec JavaScript
```bash
curl -X POST localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url":"https://spa-site.com","max_pages":10,"js":true}'
```

#### Test de santé de l'API
```bash
curl http://localhost:8000/health
```

## 📊 Format de réponse

```json
{
  "pages": 3,
  "data": [
    {
      "url": "https://example.com/",
      "status": 200,
      "title": "Titre de la page",
      "score_global": 85,
      "score_legacy": 80,
      "score_rules": 5,
      "recommendations": [
        {
          "rule_id": "META_DESC_LENGTH",
          "topic": "Meta",
          "severity": "info",
          "message": "Meta description trop longue",
          "evidence": {"length": 180}
        }
      ],
      "meta_description": "...",
      "h1_count": 1,
      "images_without_alt": 0,
      "word_count": 450
    }
  ]
}
```

## 🎯 Règles SEO analysées

### Meta & Structure
- ✅ Title (50-60 caractères)
- ✅ Meta description (150-160 caractères)
- ✅ Canonical URL
- ✅ Meta robots
- ✅ Structure H1/H2

### Accessibilité
- ✅ Images avec attribut alt
- ✅ Meta viewport
- ✅ Attribut lang sur `<html>`
- ✅ Landmarks (main, nav, header, footer)

### Social & SEO moderne
- ✅ Open Graph (og:title, og:image, og:url)
- ✅ Twitter Cards
- ✅ JSON-LD (schema.org)
- ✅ Hreflang (multi-langues)

### Performance
- ✅ Taille HTML (<400KB)
- ✅ Lazy loading images
- ✅ Formats modernes (WebP/AVIF)
- ✅ Hints de performance (preload/preconnect)

### Sécurité
- ✅ Headers de sécurité (CSP, HSTS, X-Frame-Options...)

### AEO (AI Engine Optimization)
- ✅ Fichiers `/ai.txt` et `/llms.txt` (tendance 2025)

## 🔧 Configuration avancée

### Variables d'environnement
```bash
# Port personnalisé
export PORT=3000
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Limite de pages par défaut
Modifie `max_pages` dans `app.py` ligne 23 :
```python
max_pages: Optional[int] = 60  # Change cette valeur
```

## 🚀 Déploiement

### Render.com (gratuit)
1. Fork ce repo sur GitHub
2. Connecte ton GitHub à Render.com
3. Deploy avec `render.yaml` (déjà configuré)

### Docker
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN python -m playwright install chromium
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📁 Structure du projet

```
mon-outil-seo/
├── app.py                 # API FastAPI principale
├── seo_crawler.py         # Crawler BeautifulSoup
├── seo_crawler_js.py      # Crawler Playwright (JS)
├── seo_rules.py           # 30+ règles SEO
├── requirements.txt       # Dépendances Python
├── render.yaml           # Config déploiement
├── test.html             # Interface de test
└── README.md             # Cette documentation
```

## 🐛 Problèmes courants

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Playwright not installed" (si js=true)
```bash
python -m playwright install chromium
```

### "Port already in use"
```bash
# Change le port
uvicorn app:app --port 8001
```

### Site bloqué par robots.txt
L'outil respecte le robots.txt. Si bloqué, le crawler s'arrête.

## 📈 Exemples de scores

- **🟢 90-100** : Excellent SEO
- **🟡 70-89** : Bon, quelques améliorations
- **🟠 50-69** : Moyen, optimisations nécessaires  
- **🔴 <50** : Problèmes SEO importants

## 🤝 Contribution

1. Fork le projet
2. Crée une branche : `git checkout -b ma-feature`
3. Commit : `git commit -m 'Ajoute ma feature'`
4. Push : `git push origin ma-feature`
5. Ouvre une Pull Request

## 📄 Licence

MIT License - Utilise librement !
```

Voilà ! Une doc complète avec :
- ✅ Installation claire étape par étape
- ✅ Exemples concrets de curl
- ✅ Explication des paramètres
- ✅ Format de réponse détaillé
- ✅ Liste complète des règles SEO
- ✅ Déploiement et troubleshooting

Tu peux copier ça dans un `README.md` et ton projet sera beaucoup plus professionnel ! 🚀