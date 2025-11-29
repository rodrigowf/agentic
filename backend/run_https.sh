#!/bin/bash
# Run FastAPI backend with HTTPS
cd /home/rodrigo/agentic/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --ssl-keyfile .cert/key.pem --ssl-certfile .cert/cert.pem
