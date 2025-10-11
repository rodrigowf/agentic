# Project Index

Quick reference guide to navigate the project.

---

## 🎯 Start Here

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview and setup |
| [CLAUDE.md](CLAUDE.md) | Comprehensive development guide |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Complete file structure reference |
| [ORGANIZATION_SUMMARY.md](ORGANIZATION_SUMMARY.md) | Recent organization changes |

---

## 📂 Quick Navigation

### Backend
```
backend/
├── 🚀 main.py              # Start here - FastAPI app
├── 📋 requirements.txt     # Python dependencies
├── 🔧 config/              # Configuration
├── 🧠 core/                # Agent framework
├── 🔌 api/                 # API endpoints
├── 🤖 agents/              # Agent configs (JSON)
├── 🛠️  tools/               # Custom tools
├── 🧪 tests/               # All tests
│   ├── unit/
│   └── integration/
├── 📜 scripts/             # Utility scripts
└── 📚 docs/                # Documentation
```

### Frontend
```
frontend/src/
├── 🎨 App.js               # Root component
├── 🔗 api.js               # Backend client
└── 🎭 features/            # Feature-based
    ├── agents/             # Agent management
    ├── tools/              # Tool management
    └── voice/              # Voice assistant
```

---

## 📖 Documentation

### Getting Started
- [README.md](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Main dev guide
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) - Developer guide

### Architecture
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Complete structure
- [docs/REFACTORING_SUMMARY.md](docs/REFACTORING_SUMMARY.md) - Backend refactoring
- [docs/FRONTEND_REFACTORING.md](docs/FRONTEND_REFACTORING.md) - Frontend refactoring

### Features
- [docs/VOICE_ASSISTANT_INTEGRATION_PLAN.md](docs/VOICE_ASSISTANT_INTEGRATION_PLAN.md)
- [backend/docs/MULTIMODAL_AGENT_GUIDE.md](backend/docs/MULTIMODAL_AGENT_GUIDE.md)
- [debug/AUTOMATED_UI_DEVELOPMENT.md](debug/AUTOMATED_UI_DEVELOPMENT.md)

### Testing & Tools
- [backend/tests/README.md](backend/tests/README.md) - Test guide
- [backend/scripts/README.md](backend/scripts/README.md) - Scripts guide
- [backend/docs/SCREENSHOT_FIX_GUIDE.md](backend/docs/SCREENSHOT_FIX_GUIDE.md)

---

## 🚀 Common Commands

### Start Services
```bash
./run_all.sh                 # Start both backend & frontend
./run_backend.sh             # Backend only
./run_frontend.sh            # Frontend only
```

### Backend Commands
```bash
cd backend
source venv/bin/activate

# Run tests
pytest tests/ -v
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run scripts
bash scripts/fix_x11_and_test.sh
```

### Frontend Commands
```bash
cd frontend
npm start                    # Start dev server
npm test                     # Run tests
npm run build               # Production build
```

---

## 🛠️ Development Tasks

### Add New Agent
1. Create `backend/agents/MyAgent.json`
2. See [CLAUDE.md#creating-new-agents](CLAUDE.md#creating-new-agents)

### Add New Tool
1. Create `backend/tools/my_tool.py`
2. See [CLAUDE.md#creating-new-tools](CLAUDE.md#creating-new-tools)

### Add New Test
1. Unit: `backend/tests/unit/test_my_feature.py`
2. Integration: `backend/tests/integration/test_my_integration.py`
3. See [backend/tests/README.md](backend/tests/README.md)

### Add New Documentation
1. Backend: `backend/docs/MY_DOC.md`
2. Project: `docs/MY_DOC.md`

---

## 🔍 Find Something

### Need to...
- **Configure an agent?** → `backend/agents/*.json`
- **Add a tool?** → `backend/tools/*.py`
- **Run tests?** → `backend/tests/`
- **Fix permissions?** → `backend/scripts/`
- **Read docs?** → `backend/docs/` or `docs/`
- **Debug UI?** → `debug/screenshot.js`
- **Check API?** → `backend/main.py`
- **Frontend component?** → `frontend/src/features/`

### Looking for...
- **Multimodal vision?** → [backend/docs/MULTIMODAL_AGENT_GUIDE.md](backend/docs/MULTIMODAL_AGENT_GUIDE.md)
- **Screenshot help?** → [backend/docs/SCREENSHOT_FIX_GUIDE.md](backend/docs/SCREENSHOT_FIX_GUIDE.md)
- **Voice assistant?** → [docs/VOICE_ASSISTANT_INTEGRATION_PLAN.md](docs/VOICE_ASSISTANT_INTEGRATION_PLAN.md)
- **Test examples?** → [backend/tests/README.md](backend/tests/README.md)

---

## 📞 Help & Support

### Something not working?
1. Check [CLAUDE.md#troubleshooting](CLAUDE.md#troubleshooting)
2. Check [backend/docs/](backend/docs/) for specific guides
3. Review [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for file locations

### Want to understand the code?
1. Start with [CLAUDE.md](CLAUDE.md)
2. Check [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
3. Review [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

### Need to refactor?
1. See [ORGANIZATION_SUMMARY.md](ORGANIZATION_SUMMARY.md)
2. Follow patterns in [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
3. Update documentation after changes

---

## 📊 Project Stats

**Last organized:** 2025-10-11

**Backend:**
- Agents: Multiple (see `backend/agents/`)
- Tools: 3+ custom tools
- Tests: 8+ test files (unit + integration)
- Scripts: 2 utility scripts
- Docs: 6+ documentation files

**Frontend:**
- Features: 3 (agents, tools, voice)
- Components: 10+ feature components
- Pages: 5+ feature pages

---

**Quick Tips:**
- 🎯 Always start with [CLAUDE.md](CLAUDE.md) for development
- 📂 Use [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) to find files
- 🧪 Check [backend/tests/README.md](backend/tests/README.md) before testing
- 📝 Keep README files updated when adding features

**Last updated:** 2025-10-11
