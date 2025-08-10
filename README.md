# Family Studyroom Reservation (Cloud-ready)

## Local run
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# mac/Linux
# source venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## Deploy to Render (example)
1. Push this folder to a GitHub repo.
2. In Render dashboard: New + -> Blueprint, select this repo (because `render.yaml` exists).
3. Render will create:
   - Web Service
   - PostgreSQL database
4. After deploy, open the web URL. The app auto-migrates on first run.

> Other providers (Railway, Fly.io, etc.) also work. Use `DATABASE_URL` and run with Gunicorn.
