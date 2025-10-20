# Project Structure

**Last Updated:** 2025-10-11

This document provides a comprehensive overview of the project's file organization.

---

## Directory Tree

```
/home/rodrigo/agentic/
├── backend/                           # Python FastAPI backend
│   ├── main.py                        # FastAPI application entry point
│   ├── requirements.txt               # Python dependencies
│   ├── run.sh                         # Backend startup script
│   ├── .env                           # Environment variables (API keys, etc.)
│   │
│   ├── config/                        # Configuration & data models
│   │   ├── __init__.py
│   │   ├── schemas.py                 # Pydantic models for validation
│   │   └── config_loader.py           # Load agents/tools from disk
│   │
│   ├── utils/                         # Utility modules
│   │   ├── __init__.py
│   │   ├── context.py                 # Agent context management
│   │   └── voice_conversation_store.py # SQLite voice storage
│   │
│   ├── core/                          # Core agent framework
│   │   ├── __init__.py
│   │   ├── agent_factory.py           # Create agents from configs
│   │   ├── runner.py                  # Execute agents via WebSocket
│   │   ├── looping_agent.py           # Single agent with tool loop
│   │   ├── looping_code_executor_agent.py # Agent with code execution
│   │   ├── multimodal_tools_looping_agent.py # Vision-capable agent
│   │   └── nested_agent.py            # Multi-agent coordinator
│   │
│   ├── api/                           # API-specific modules
│   │   ├── __init__.py
│   │   ├── realtime_voice.py          # OpenAI Realtime Voice API
│   │   └── claude_code_controller.py  # Claude Code CLI integration
│   │
│   ├── agents/                        # Agent configurations (JSON)
│   │   ├── MainConversation.json      # Nested team agent example
│   │   ├── MultimodalVisionAgent.json # Vision agent example
│   │   ├── Manager.json
│   │   ├── Developer.json
│   │   ├── Researcher.json
│   │   └── ... (other agent configs)
│   │
│   ├── tools/                         # Custom tool implementations
│   │   ├── memory.py                  # Memory tools (ChromaDB)
│   │   ├── research.py                # Web search & fetch tools
│   │   └── image_tools.py             # Screenshot & image generation
│   │
│   ├── tests/                         # Test suite
│   │   ├── README.md                  # Test documentation
│   │   ├── test_image_tools.py        # Image tools test suite
│   │   ├── unit/                      # Unit tests
│   │   │   ├── test_screenshot.py
│   │   │   └── test_working_image_tools.py
│   │   └── integration/               # Integration tests
│   │       ├── test_claude_code_permissions.py
│   │       ├── test_multimodal_api.py
│   │       ├── test_multimodal_integration.py
│   │       ├── test_real_screenshot.py
│   │       ├── test_system_message_update.py
│   │       └── test_voice_claude_integration.py
│   │
│   ├── scripts/                       # Utility scripts
│   │   ├── README.md                  # Scripts documentation
│   │   ├── fix_x11_and_test.sh        # Fix X11 permissions & test
│   │   └── fix_gnome_screenshot.sh    # Fix GNOME screenshot tool
│   │
│   ├── docs/                          # Backend-specific documentation
│   │   ├── SCREENSHOT_FIX_GUIDE.md
│   │   ├── SCREENSHOT_TESTING_REPORT.md
│   │   ├── SCREENSHOT_TEST_SUMMARY.md
│   │   ├── SCREENSHOT_TOOL_README.md
│   │   ├── MULTIMODAL_AGENT_GUIDE.md
│   │   └── MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md
│   │
│   ├── workspace/                     # Agent workspace
│   │   ├── screenshots/               # Screenshots from agents
│   │   ├── test_image.png
│   │   ├── sample_chart.png
│   │   └── ... (other generated files)
│   │
│   ├── venv/                          # Python virtual environment
│   └── voice_conversations.db         # SQLite voice conversation storage
│
├── frontend/                          # React application
│   ├── package.json
│   ├── public/                        # Static assets
│   │   └── index.html
│   │
│   └── src/
│       ├── index.js                   # App entry point
│       ├── App.js                     # Root component
│       ├── api.js                     # Backend API client
│       │
│       ├── features/                  # Feature-based architecture
│       │   ├── agents/                # Agent management feature
│       │   │   ├── components/
│       │   │   │   ├── AgentEditor.js
│       │   │   │   ├── RunConsole.js
│       │   │   │   └── LogMessageDisplay.js
│       │   │   └── pages/
│       │   │       └── AgentDashboard.js
│       │   │
│       │   ├── tools/                 # Tool management feature
│       │   │   ├── components/
│       │   │   │   ├── ToolEditor.js
│       │   │   │   └── CodeEditor.js
│       │   │   └── pages/
│       │   │       └── ToolsDashboard.js
│       │   │
│       │   └── voice/                 # Voice assistant feature
│       │       ├── components/
│       │       │   ├── VoiceSessionControls.js
│       │       │   ├── AudioVisualizer.js
│       │       │   ├── ConversationHistory.js
│       │       │   ├── NestedAgentInsights.js
│       │       │   └── ClaudeCodeInsights.js
│       │       └── pages/
│       │           ├── VoiceAssistant.js
│       │           └── VoiceDashboard.js
│       │
│       └── shared/                    # Shared components
│           └── components/
│
├── debug/                             # Debugging tools
│   ├── screenshot.js                  # Puppeteer screenshot automation
│   ├── screenshots/                   # Screenshot output directory
│   ├── export_voice_conversations.py  # Export SQLite to JSON
│   ├── db_exports/                    # Database exports
│   │   └── voice_conversations/       # Voice conversation JSON exports
│   ├── AUTOMATED_UI_DEVELOPMENT.md    # UI dev workflow guide
│   └── package.json                   # Debug tools dependencies
│
├── docs/                              # Root-level documentation
│   ├── DEVELOPER_GUIDE.md
│   ├── REFACTORING_SUMMARY.md         # Backend refactoring notes
│   ├── FRONTEND_REFACTORING.md        # Frontend refactoring notes
│   ├── VOICE_ASSISTANT_INTEGRATION_PLAN.md
│   ├── autogen-multimodality.md
│   ├── nested_instructions.md
│   ├── enhance_chat.md
│   ├── enhancements_gpt-research.md
│   ├── deepresearch_enhancements_instructions.md
│   └── instructions-from-gpt.md
│
├── logs/                              # Application logs
│   ├── frontend.log
│   └── voice_exports/
│
├── workspace/                         # Root workspace (if needed)
│
├── CLAUDE.md                          # Main development guide
├── PROJECT_STRUCTURE.md               # This file
├── README.md                          # Project README
├── PERMISSION_FIX_SUMMARY.md          # Permission fixes documentation
├── install.sh                         # Installation script
├── run_all.sh                         # Start both backend & frontend
├── run_backend.sh                     # Start backend only
├── run_frontend.sh                    # Start frontend only
└── test_runner.py                     # Test runner script

```

---

## Quick Navigation

### Starting Points

| What | Where |
|------|-------|
| **Main development guide** | [CLAUDE.md](CLAUDE.md) |
| **Project README** | [README.md](README.md) |
| **Backend entry point** | [backend/main.py](backend/main.py) |
| **Frontend entry point** | [frontend/src/App.js](frontend/src/App.js) |

### Common Tasks

| Task | Location |
|------|----------|
| **Add new agent** | Create JSON in [backend/agents/](backend/agents/) |
| **Add new tool** | Create Python module in [backend/tools/](backend/tools/) |
| **Add new test** | Add to [backend/tests/unit/](backend/tests/unit/) or [backend/tests/integration/](backend/tests/integration/) |
| **Add backend docs** | Add to [backend/docs/](backend/docs/) |
| **Add frontend feature** | Create in [frontend/src/features/](frontend/src/features/) |
| **Add utility script** | Create in [backend/scripts/](backend/scripts/) |

### Key Configuration Files

| File | Purpose |
|------|---------|
| [backend/requirements.txt](backend/requirements.txt) | Python dependencies |
| [backend/.env](backend/.env) | API keys, environment variables |
| [frontend/package.json](frontend/package.json) | Node.js dependencies |
| [backend/agents/*.json](backend/agents/) | Agent configurations |

---

## Directory Purposes

### Backend Directories

#### `/backend/config/`
**Purpose:** Configuration loading and data validation
- `schemas.py` - Pydantic models for type safety
- `config_loader.py` - Load agents and tools from disk

#### `/backend/utils/`
**Purpose:** Shared utility functions
- `context.py` - Thread-local agent context
- `voice_conversation_store.py` - SQLite voice storage

#### `/backend/core/`
**Purpose:** Core agent framework implementation
- Agent factories, runners, and implementations
- All agent types (looping, nested, multimodal, code executor)

#### `/backend/api/`
**Purpose:** API-specific modules
- Voice assistant integration
- Claude Code CLI controller

#### `/backend/agents/`
**Purpose:** Agent configuration files (JSON)
- Each file defines one agent's behavior
- Loaded dynamically by config_loader

#### `/backend/tools/`
**Purpose:** Custom tool implementations
- Python modules with FunctionTool instances
- Auto-discovered by config_loader

#### `/backend/tests/`
**Purpose:** All test files
- `unit/` - Fast, isolated tests
- `integration/` - Multi-component tests

#### `/backend/scripts/`
**Purpose:** Development and maintenance scripts
- Setup scripts
- Testing scripts
- Utility scripts

#### `/backend/docs/`
**Purpose:** Backend-specific documentation
- Implementation guides
- Testing reports
- Technical documentation

#### `/backend/workspace/`
**Purpose:** Runtime workspace for agents
- Screenshots
- Generated files
- Temporary storage

### Frontend Directories

#### `/frontend/src/features/`
**Purpose:** Feature-based organization
- `agents/` - Agent management UI
- `tools/` - Tool management UI
- `voice/` - Voice assistant UI

Each feature has:
- `components/` - Feature-specific components
- `pages/` - Full-page views

#### `/frontend/src/shared/`
**Purpose:** Shared/reusable components
- Components used across features

### Other Directories

#### `/debug/`
**Purpose:** Development debugging tools
- Screenshot automation
- Database exporters
- Development workflows

#### `/docs/`
**Purpose:** Root-level documentation
- Project-wide documentation
- Planning documents
- Refactoring notes

#### `/logs/`
**Purpose:** Application logs
- Frontend logs
- Export logs

---

## File Naming Conventions

### Python Files
- **Modules:** `lowercase_with_underscores.py`
- **Tests:** `test_<component>.py`
- **Scripts:** `<action>_<target>.sh`

### JavaScript Files
- **Components:** `PascalCase.js`
- **Utilities:** `camelCase.js`
- **Tests:** `ComponentName.test.js`

### Documentation
- **Guides:** `ALL_CAPS.md`
- **READMEs:** `README.md`
- **Notes:** `lowercase-with-hyphens.md`

### Configuration
- **Agent configs:** `AgentName.json`
- **Package configs:** `package.json`, `requirements.txt`
- **Environment:** `.env`

---

## Adding New Components

### New Agent
1. Create `/backend/agents/MyAgent.json`
2. Define configuration (see CLAUDE.md)
3. Test via frontend at `/agents/MyAgent`

### New Tool
1. Create `/backend/tools/my_tool.py`
2. Implement with FunctionTool
3. Export in `tools = [...]`
4. Tool auto-discovered on backend restart

### New Test
1. Unit test: `/backend/tests/unit/test_my_feature.py`
2. Integration: `/backend/tests/integration/test_my_integration.py`
3. Run with `pytest tests/`

### New Script
1. Create `/backend/scripts/my_script.sh`
2. Add shebang `#!/bin/bash`
3. Make executable: `chmod +x scripts/my_script.sh`
4. Document in `/backend/scripts/README.md`

### New Documentation
1. Backend-specific: `/backend/docs/MY_DOC.md`
2. Project-wide: `/docs/MY_DOC.md`
3. Update this file if structure changes

---

## Recent Reorganization (2025-10-11)

The project was recently reorganized for better maintainability:

### What Changed

**Tests moved:**
- ❌ `backend/test_*.py` (scattered)
- ✅ `backend/tests/unit/` and `backend/tests/integration/` (organized)

**Scripts moved:**
- ❌ `backend/*.sh` (mixed with code)
- ✅ `backend/scripts/` (dedicated directory)

**Documentation moved:**
- ❌ `backend/*.md` (scattered)
- ✅ `backend/docs/` (organized)

### Benefits

- ✅ Clearer separation of concerns
- ✅ Easier to find files
- ✅ Better for CI/CD integration
- ✅ Follows Python best practices

---

## Development Workflow

### Running Tests
```bash
cd backend
source venv/bin/activate
pytest tests/unit/ -v       # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/               # All tests
```

### Running Scripts
```bash
cd backend
bash scripts/fix_x11_and_test.sh
bash scripts/fix_gnome_screenshot.sh
```

### Viewing Documentation
```bash
# Backend docs
ls backend/docs/

# Project docs
ls docs/

# Feature READMEs
cat backend/tests/README.md
cat backend/scripts/README.md
```

---

## Maintenance

### When Adding New Files

1. **Follow naming conventions** (see above)
2. **Place in appropriate directory** (see directory purposes)
3. **Update this document** if adding new directories
4. **Add README** if creating new directory structure
5. **Update CLAUDE.md** if affecting development workflow

### When Refactoring

1. **Move related files together**
2. **Update all import statements**
3. **Update script paths**
4. **Update documentation**
5. **Test after refactoring**

### Keeping Organized

- Regular cleanup of workspace directories
- Remove obsolete test files
- Archive old documentation
- Keep README files up to date

---

**Last Updated:** 2025-10-11
**Maintained By:** Development team
**Questions?** See [CLAUDE.md](CLAUDE.md) for comprehensive development guide
