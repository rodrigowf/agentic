# Documentation Index

**Last Updated:** 2025-12-04

Complete documentation map for the agentic AI system.

---

## 🚀 Getting Started (Start Here)

New to this project? Follow this path:

1. **[QUICK_START.md](QUICK_START.md)** - Get running in 5 minutes
2. **[guides/OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md)** - Understand your environment
3. **[../CLAUDE.md](../CLAUDE.md)** - Main guide with overview and references

---

## 📖 Core Documentation

### Main Guides (docs/ root)

| Document | Purpose | Size |
|----------|---------|------|
| **[QUICK_START.md](QUICK_START.md)** | 5-minute setup guide | Essential |
| **[../CLAUDE.md](../CLAUDE.md)** | Streamlined main guide with references | 463 lines |
| **[CLAUDE_FULL_ORIGINAL.md](CLAUDE_FULL_ORIGINAL.md)** | Complete detailed guide (archived) | 3,053 lines |
| **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** | This file - complete doc map | Reference |
| **[webrtc-bridge-notes.md](webrtc-bridge-notes.md)** | WebRTC migration notes and architecture | Technical |
| **[WEBRTC_INTERACTIVE_TESTING.md](WEBRTC_INTERACTIVE_TESTING.md)** | Comprehensive WebRTC testing guide | Testing |

---

## 📚 Development Guides

### guides/ - Feature-Specific Guides

| Guide | Purpose |
|-------|---------|
| **[OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md)** | Context detection and behavior (Local vs Production) |
| **[DEVELOPER_GUIDE.md](guides/DEVELOPER_GUIDE.md)** | In-depth architecture and development |
| **[AGENT_DEVELOPMENT_GUIDE.md](guides/AGENT_DEVELOPMENT_GUIDE.md)** | Creating and configuring agents |
| **[TOOL_DEVELOPMENT_GUIDE.md](guides/TOOL_DEVELOPMENT_GUIDE.md)** | Creating custom tools |
| **[MULTIMODAL_AGENT_GUIDE.md](guides/MULTIMODAL_AGENT_GUIDE.md)** | Vision-capable agents |
| **[DYNAMIC_INIT_AGENT_IMPLEMENTATION.md](guides/DYNAMIC_INIT_AGENT_IMPLEMENTATION.md)** | Custom agent initialization |
| **[DYNAMIC_AGENT_DESCRIPTION_INJECTION.md](guides/DYNAMIC_AGENT_DESCRIPTION_INJECTION.md)** | Automatic orchestrator info |
| **[DATABASE_AGENT_GUIDE.md](guides/DATABASE_AGENT_GUIDE.md)** | MongoDB database management (10 tools) |
| **[DATABASE_AND_MEMORY_SETUP.md](guides/DATABASE_AND_MEMORY_SETUP.md)** | MongoDB & ChromaDB setup |
| **[API_AGENT_GUIDE.md](guides/API_AGENT_GUIDE.md)** | Web API interaction agent |
| **[MOBILE_VOICE_GUIDE.md](guides/MOBILE_VOICE_GUIDE.md)** | Smartphone as wireless microphone |
| **[SCREENSHOT_TOOL_README.md](guides/SCREENSHOT_TOOL_README.md)** | Screenshot automation |
| **[autogen-multimodality.md](guides/autogen-multimodality.md)** | Base64 images in AutoGen |
| **[KEYBOARD_NAVIGATION_GUIDE.md](guides/KEYBOARD_NAVIGATION_GUIDE.md)** | Keyboard shortcuts |
| **[SPATIAL_NAVIGATION_GUIDE.md](guides/SPATIAL_NAVIGATION_GUIDE.md)** | Arrow key navigation |
| **[TV_NAVIGATION_GUIDE.md](guides/TV_NAVIGATION_GUIDE.md)** | TV remote control |

---

## 🏗️ System Architecture

### architecture/ - Design and Implementation

| Document | Purpose |
|----------|---------|
| **[REFACTORING_SUMMARY.md](architecture/REFACTORING_SUMMARY.md)** | Backend modular structure |
| **[FRONTEND_REFACTORING.md](architecture/FRONTEND_REFACTORING.md)** | Feature-based frontend architecture |
| **[MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md](architecture/MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md)** | Vision agent internals |
| **[VOICE_ASSISTANT_INTEGRATION_PLAN.md](architecture/VOICE_ASSISTANT_INTEGRATION_PLAN.md)** | Voice system architecture |
| **[WEBRTC_MOBILE_VOICE_ARCHITECTURE.md](architecture/WEBRTC_MOBILE_VOICE_ARCHITECTURE.md)** | Mobile voice P2P architecture |

---

## 🚀 Deployment & Operations

### deployment/ - Production Setup

| Document | Purpose |
|----------|---------|
| **[DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)** | Complete installation instructions |
| **[DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md)** | Step-by-step deployment verification |
| **[DEPLOYMENT_INDEX.md](deployment/DEPLOYMENT_INDEX.md)** | Deployment documentation map |
| **[JETSON_DEPLOYMENT_GUIDE.md](deployment/JETSON_DEPLOYMENT_GUIDE.md)** | Jetson Nano production server |
| **[JETSON_OPERATIONS_GUIDE.md](deployment/JETSON_OPERATIONS_GUIDE.md)** | Maintain and update Jetson |
| **[JETSON_DEPENDENCY_FIXES.md](deployment/JETSON_DEPENDENCY_FIXES.md)** | ARM64 dependency solutions |
| **[SERVER_HUB_DEPLOYMENT.md](deployment/SERVER_HUB_DEPLOYMENT.md)** | Multi-app nginx setup |

---

## 🐛 Troubleshooting & Fixes

### troubleshooting/ - Solutions and Debugging

| Document | Purpose |
|----------|---------|
| **[SCREENSHOT_FIX_GUIDE.md](troubleshooting/SCREENSHOT_FIX_GUIDE.md)** | Fix GNOME Wayland screenshot issues |
| **[MOBILE_VOICE_FIXES.md](troubleshooting/MOBILE_VOICE_FIXES.md)** | Audio playback and database issues |
| **[HTTPS_MOBILE_VOICE_FIX.md](troubleshooting/HTTPS_MOBILE_VOICE_FIX.md)** | Nginx WebRTC HTTPS configuration |
| **[MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md](troubleshooting/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md)** | ADB debugging workflow |
| **[DESKTOP_SPEAKER_MUTE_FIX.md](troubleshooting/DESKTOP_SPEAKER_MUTE_FIX.md)** | Echo elimination |
| **[CONTINUOUS_VOICE_FIX.md](troubleshooting/CONTINUOUS_VOICE_FIX.md)** | Buffer size optimization |
| **[TV_WEBVIEW_FIX_SUMMARY.md](troubleshooting/TV_WEBVIEW_FIX_SUMMARY.md)** | Nginx try_files with alias |
| **[URL_FIX_IMPLEMENTATION.md](troubleshooting/URL_FIX_IMPLEMENTATION.md)** | Centralized URL builder |
| **[URL_RESOLUTION_STRATEGY.md](troubleshooting/URL_RESOLUTION_STRATEGY.md)** | URL resolution patterns |
| **[KEYBOARD_NAVIGATION_FIX.md](troubleshooting/KEYBOARD_NAVIGATION_FIX.md)** | Router context error |
| **[LIGHT_MODE_FIX_SUMMARY.md](troubleshooting/LIGHT_MODE_FIX_SUMMARY.md)** | Light mode UI fixes |
| **[PERMISSION_FIX_SUMMARY.md](troubleshooting/PERMISSION_FIX_SUMMARY.md)** | Claude Code bypass permissions |

---

## 📦 Reference & Examples

### references/ - Code References

| Document | Purpose |
|----------|---------|
| **[README.md](references/README.md)** | AutoGen examples, legacy code, Jupyter notebooks |

**Contains:**
- Python reference files (AssistantAgent.py, memory.py, vectorstore.py)
- Jupyter notebooks (group-chat.ipynb, multimodality-images.ipynb)
- AutoGen migration guide (v0.2 to v0.4)

---

## 📂 Archive

### archive/ - Historical Documents

Documents kept for historical reference (may be outdated).

**Contains:**
- Session summaries
- Old agent analyses
- Deprecated enhancement plans
- Previous debugging logs
- Documentation audit reports

See [archive/](archive/) for complete list.

---

## 📊 Documentation Structure

```
docs/
├── QUICK_START.md                      # 5-minute setup
├── DOCUMENTATION_INDEX.md              # This file
├── CLAUDE_FULL_ORIGINAL.md             # Complete detailed guide
├── webrtc-bridge-notes.md              # WebRTC migration notes
├── WEBRTC_INTERACTIVE_TESTING.md       # WebRTC testing guide
│
├── guides/                             # 16 feature guides
│   ├── OPERATIONAL_CONTEXT.md
│   ├── DEVELOPER_GUIDE.md
│   ├── AGENT_DEVELOPMENT_GUIDE.md
│   ├── TOOL_DEVELOPMENT_GUIDE.md
│   ├── DATABASE_AND_MEMORY_SETUP.md
│   └── ...
│
├── architecture/                       # 5 architecture docs
│   ├── REFACTORING_SUMMARY.md
│   ├── FRONTEND_REFACTORING.md
│   └── ...
│
├── deployment/                         # 7 deployment docs
│   ├── DEPLOYMENT_GUIDE.md
│   ├── JETSON_DEPLOYMENT_GUIDE.md
│   └── ...
│
├── troubleshooting/                    # 12 troubleshooting docs
│   ├── MOBILE_VOICE_FIXES.md
│   ├── SCREENSHOT_FIX_GUIDE.md
│   └── ...
│
├── references/                         # Code examples
│   └── README.md (+ Python files, notebooks)
│
└── archive/                            # Historical documents
    └── (27 archived files)
```

---

## 🔍 Quick Reference

### By Topic

| Topic | Document |
|-------|----------|
| **Getting started** | [QUICK_START.md](QUICK_START.md) |
| **Context detection** | [OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md) |
| **Creating agents** | [AGENT_DEVELOPMENT_GUIDE.md](guides/AGENT_DEVELOPMENT_GUIDE.md) |
| **Creating tools** | [TOOL_DEVELOPMENT_GUIDE.md](guides/TOOL_DEVELOPMENT_GUIDE.md) |
| **Voice system** | [WEBRTC_INTERACTIVE_TESTING.md](WEBRTC_INTERACTIVE_TESTING.md) |
| **Mobile voice** | [MOBILE_VOICE_GUIDE.md](guides/MOBILE_VOICE_GUIDE.md) |
| **Database setup** | [DATABASE_AND_MEMORY_SETUP.md](guides/DATABASE_AND_MEMORY_SETUP.md) |
| **Deployment** | [JETSON_DEPLOYMENT_GUIDE.md](deployment/JETSON_DEPLOYMENT_GUIDE.md) |
| **Debugging** | [troubleshooting/](troubleshooting/) |
| **Architecture** | [REFACTORING_SUMMARY.md](architecture/REFACTORING_SUMMARY.md) |

### By Task

| Task | Document |
|------|----------|
| **Start development servers** | [QUICK_START.md](QUICK_START.md#2-start-backend-local-development) |
| **Test voice system** | [WEBRTC_INTERACTIVE_TESTING.md](WEBRTC_INTERACTIVE_TESTING.md) |
| **Take screenshots** | [SCREENSHOT_TOOL_README.md](guides/SCREENSHOT_TOOL_README.md) |
| **Deploy to Jetson** | [JETSON_DEPLOYMENT_GUIDE.md](deployment/JETSON_DEPLOYMENT_GUIDE.md) |
| **Debug WebRTC** | [webrtc-bridge-notes.md](webrtc-bridge-notes.md) |
| **Setup database** | [DATABASE_AND_MEMORY_SETUP.md](guides/DATABASE_AND_MEMORY_SETUP.md) |
| **Fix mobile voice** | [MOBILE_VOICE_FIXES.md](troubleshooting/MOBILE_VOICE_FIXES.md) |

---

## 📝 Documentation Statistics

**Total Files:** 68 markdown files

**By Category:**
- **Root:** 5 files (main guides)
- **guides/:** 16 files (feature-specific)
- **architecture/:** 5 files (system design)
- **deployment/:** 7 files (production setup)
- **troubleshooting/:** 12 files (fixes and debugging)
- **references/:** 1 file (+ code examples)
- **archive/:** 27 files (historical)

**Cleanup (2025-12-04):**
- Removed 30 outdated files (Pipecat, redundant WebRTC, completed refactors)
- Streamlined main CLAUDE.md (87% reduction)
- Created focused topic guides
- Organized into clear category structure

---

## 🔧 Maintenance Guidelines

### When Adding Documentation

1. **Choose correct location:**
   - `guides/` - How-to and feature guides
   - `architecture/` - System design and technical architecture
   - `deployment/` - Installation, deployment, operations
   - `troubleshooting/` - Bug fixes, debugging, solutions
   - `archive/` - Outdated or historical documents

2. **Update this index** - Add entry to appropriate section

3. **Update CLAUDE.md** - If it's a critical reference document

4. **Link from related docs** - Add cross-references where relevant

### When Removing Documentation

1. **Move to archive/** if it has historical value
2. **Delete completely** if truly obsolete
3. **Update all links** that referenced the removed doc
4. **Update this index**

### Naming Conventions

- **Guides:** `FEATURE_GUIDE.md` or `FEATURE_NAME_GUIDE.md`
- **Architecture:** `COMPONENT_ARCHITECTURE.md` or `SYSTEM_DESIGN.md`
- **Deployment:** `DEPLOYMENT_*.md` or `SYSTEM_NAME_DEPLOYMENT.md`
- **Troubleshooting:** `FEATURE_FIX.md` or `ISSUE_NAME_FIX.md`
- **Use UPPERCASE** for file names (consistency with existing docs)

---

## 🎯 Common Use Cases

### New Developer Onboarding
1. [QUICK_START.md](QUICK_START.md) - Setup environment
2. [OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md) - Understand contexts
3. [DEVELOPER_GUIDE.md](guides/DEVELOPER_GUIDE.md) - Deep dive into system
4. [CLAUDE.md](../CLAUDE.md) - Reference guide

### Production Deployment
1. [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) - General deployment
2. [JETSON_DEPLOYMENT_GUIDE.md](deployment/JETSON_DEPLOYMENT_GUIDE.md) - Jetson specific
3. [DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md) - Verify deployment

### Feature Development
1. [AGENT_DEVELOPMENT_GUIDE.md](guides/AGENT_DEVELOPMENT_GUIDE.md) - Create agents
2. [TOOL_DEVELOPMENT_GUIDE.md](guides/TOOL_DEVELOPMENT_GUIDE.md) - Create tools
3. [architecture/](architecture/) - Understand system design

### Debugging Issues
1. [troubleshooting/](troubleshooting/) - Browse fix documents
2. [WEBRTC_INTERACTIVE_TESTING.md](WEBRTC_INTERACTIVE_TESTING.md) - Test voice system
3. [webrtc-bridge-notes.md](webrtc-bridge-notes.md) - WebRTC architecture

---

**For complete project documentation, see [../CLAUDE.md](../CLAUDE.md)**

**Last Updated:** 2025-12-04
**Total Documentation:** 68 files organized in 7 categories
