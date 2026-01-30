Production deployment notes
==========================

This file documents simple production deployment options for the Video-RAG project.

1) Systemd service (recommended for single server)

- Place `backend/.env` with production values (DB, API keys, etc.).
- Build frontend once on the host (or as part of CI):

```bash
cd /home/codenza/Finalproject/video-rag-app
npm ci --production
npm run build
```

- Create a systemd service file at `/etc/systemd/system/videorag.service` (example below).

- Reload systemd and enable service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now videorag.service
sudo journalctl -u videorag.service -f
```

2) Docker / Docker Compose

- Build and run using the included `docker-compose.yml` (recommended for containerized hosts).

```bash
# from project root
docker-compose -f docker-compose.yml up --build -d
```

If the host's `docker` requires sudo, either use `sudo` or add your user to the `docker` group.

3) Service file example (systemd)

Create `/etc/systemd/system/videorag.service` with the following content (adjust `User`, paths and `PYTHON` as needed):

```ini
[Unit]
Description=Video-RAG API (uvicorn)
After=network.target

[Service]
Type=simple
User=codenza
WorkingDirectory=/home/codenza/Finalproject/backend
Environment=PYTHONPATH=/home/codenza/Finalproject
Environment=PATH=/home/codenza/.local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3.11 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Notes:
- For production, consider running UVicorn behind a reverse proxy (nginx) and adding TLS.
- Tune `--workers` to the number of CPU cores for better concurrency (or use gunicorn + uvicorn workers).
- Ensure `backend/.env` contains any required secrets and that file permissions are protected.

API key protection
- The repository includes a simple API-key protection for sensitive endpoints (LLM/chat/quiz/video processing).
- Set `API_KEY` in `backend/.env` by adding `API_KEY=your-secret-key` (do not commit this file).
- Clients must send the key in the `X-API-Key` header or `Authorization: Bearer <key>` when calling protected endpoints.

Example (curl):
```bash
curl -H "X-API-Key: your-secret-key" -X POST http://your-server/api/chat -d '{"videoId":"...","message":"Hello"}' -H "Content-Type: application/json"
```

Using Docker secrets (recommended for containers)
- Create Docker secrets on the host and reference them in a production compose file. The app will automatically load secrets mounted at `/run/secrets/<NAME>`.

Example (create secrets):
```bash
echo -n "your-openai-key" | docker secret create OPENAI_API_KEY -
echo -n "your-google-key" | docker secret create GOOGLE_API_KEY -
echo -n "your-app-api-key" | docker secret create API_KEY -
```

In the `docker-compose.prod.yml` include the secrets and mount them for the backend service. The backend will read `/run/secrets/OPENAI_API_KEY` etc.

AWS Secrets Manager (optional)
- If you use AWS Secrets Manager, name your secrets `video-rag/openai` and `video-rag/google` (or update the names in `backend/app/config.py`). When `boto3` and AWS credentials are available, the service will attempt to read those secrets at startup.

Local developer secrets
- For local development you can create `backend/.secrets/OPENAI_API_KEY` etc. — these files are read into environment variables automatically and are ignored by default from source control.

Security note: never commit secrets into the repository or into CI logs. Use your cloud provider or a secrets manager and restrict access to service principals/CI tokens.