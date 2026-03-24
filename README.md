# Franckate Cipher API — Deployment Guide

## Project structure

```
franckate-api/
├── backend/
│   ├── app.py            ← Flask API
│   ├── cipher.py         ← Cipher engine
│   ├── requirements.txt
│   ├── Procfile          ← For Render
│   └── render.yaml       ← One-click Render deploy
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## Deploy the backend to Render (free)

### Option A — One-click (recommended)

1. Push the `backend/` folder to a GitHub repo
2. Go to [render.com](https://render.com) → New → **Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` and set everything up
5. Click **Deploy**
6. Your API will be live at: `https://your-app-name.onrender.com`

### Option B — Manual setup on Render

1. Create account at [render.com](https://render.com)
2. New → Web Service → connect repo
3. Settings:
   - **Environment**: Python
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app --workers=2 --bind=0.0.0.0:$PORT`
4. Environment variables (add these in Render dashboard):
   - `SECRET_KEY` → click "Generate" for a random value
   - `DATABASE_URL` → add a Render Postgres database and paste its URL
5. Deploy

### Option C — Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your backend repo
3. Add a Postgres plugin
4. Set env vars: `SECRET_KEY`, `DATABASE_URL` (Railway fills this automatically)
5. Deploy → your URL appears in the dashboard

---

## Deploy the frontend to Vercel (free)

1. Push the `frontend/` folder to a GitHub repo (can be same or different repo)
2. Go to [vercel.com](https://vercel.com) → New Project → Import repo
3. Framework: **Other** (static site, no framework needed)
4. Root directory: `frontend/` (if monorepo) or `/` (if separate repo)
5. **Before deploying**: Update `API_BASE` in `frontend/app.js`:
   ```js
   // Change this line:
   const API_BASE = "https://franckate-api.onrender.com/api";
   // To your actual Render URL:
   const API_BASE = "https://YOUR-RENDER-APP-NAME.onrender.com/api";
   ```
6. Deploy → your docs site is live at `https://your-site.vercel.app`

### Alternative: Netlify

1. Drag-and-drop the `frontend/` folder to [netlify.com/drop](https://app.netlify.com/drop)
2. Done — instant deploy with a `.netlify.app` URL

---

## Local development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
# API running at http://127.0.0.1:5000
```

### Frontend
Open `frontend/index.html` in your browser **or** serve it:
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

For local dev, edit `frontend/app.js` line 2:
```js
const API_BASE = "http://127.0.0.1:5000/api";
```

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask secret key — use a long random string |
| `DATABASE_URL` | No | Postgres URL. Defaults to SQLite if not set |
| `PORT` | Auto | Set by Render/Railway automatically |

---

## Testing your deployment

```bash
# Health check (no key needed)
curl https://YOUR-API-URL/api/health

# Get API info (no key needed)
curl https://YOUR-API-URL/api/info

# Register
curl -X POST https://YOUR-API-URL/api/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"mypassword"}'

# Encrypt (use the api_key from the register response)
curl -X POST https://YOUR-API-URL/api/encrypt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY_HERE" \
  -d '{"text":"Hello World"}'
```

---

## Giving your API key to students

Share this quickstart with your class:

```python
# pip install requests
import requests

API_KEY = "get yours at YOUR-FRONTEND-URL"
BASE = "https://YOUR-API-URL/api"

# Encrypt
r = requests.post(f"{BASE}/encrypt",
    headers={"X-API-Key": API_KEY},
    json={"text": "Hello World"})
print(r.json()["encrypted"])

# Decrypt
r = requests.post(f"{BASE}/decrypt",
    headers={"X-API-Key": API_KEY},
    json={"text": "U7.L4.L11.L11.L14."})
print(r.json()["decrypted"])

# See how it works step by step
r = requests.post(f"{BASE}/encrypt/steps",
    headers={"X-API-Key": API_KEY},
    json={"text": "Hi"})
for step in r.json()["steps"]:
    print(step["explanation"])
```

---

## Updating the API URL in the frontend

Once deployed, update `frontend/app.js`:
```js
const API_BASE = "https://YOUR-RENDER-APP.onrender.com/api";
```

And optionally update `backend/app.py` info endpoint:
```python
"docs": "https://YOUR-VERCEL-SITE.vercel.app",
```
