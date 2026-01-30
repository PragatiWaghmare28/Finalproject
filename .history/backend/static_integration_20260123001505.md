Instructions to serve the built frontend with the FastAPI backend

1) Build the frontend

   cd video-rag-app
   npm install
   npm run build

   The build artifacts will be in `video-rag-app/dist`.

2) Start the backend (it will serve the static files)

   # from workspace root
   PYTHONPATH=. python3.11 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

3) The frontend will be available at `http://127.0.0.1:8000/` and backend API at `/api/*`.

Note: I added `StaticFiles` mounting in `backend/app/main.py`.
