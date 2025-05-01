# AutoGen Agent Dashboard

This repository contains:

- **backend/**: FastAPI server powered by AutoGen v0.5.3 for managing and running agents.
- **frontend/**: React + Material UI dashboard to create/edit agents, tools, and view live runs.

## Prerequisites

- Python 3.10+
- Node.js 16+
- GitHub Copilot in Edit mode

## Setup

### Backend
```bash
cd backend
cp .env.example .env        # fill in your API keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
cp .env.local.example .env.local  # adjust URLs if needed
npm install
npm start
```