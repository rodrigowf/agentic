# Documentation Index

**Last Updated:** 2025-12-01

This index provides a comprehensive guide to all documentation in the Agentic project.

---

## 📖 Essential Reading (Start Here)

| Document | Purpose | Location |
|----------|---------|----------|
| **[README.md](../README.md)** | Project overview, quick start, core capabilities | Root |
| **[CLAUDE.md](../CLAUDE.md)** | Comprehensive developer guide for Claude instances | Root |
| **[Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)** | Complete installation instructions | docs/deployment/ |

---

## 🏗️ Architecture & Design

Understand how the system is built and why.

| Document | Purpose |
|----------|---------|
| **[Developer Guide](guides/DEVELOPER_GUIDE.md)** | In-depth architecture, components, and extension points |
| **[Frontend Refactoring](architecture/FRONTEND_REFACTORING.md)** | Feature-based frontend architecture |
| **[Backend Refactoring](architecture/REFACTORING_SUMMARY.md)** | Modular backend structure |
| **[Multimodal Agent Implementation](architecture/MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md)** | Vision agent technical architecture |
| **[WebRTC Architecture](architecture/WEBRTC_MOBILE_VOICE_ARCHITECTURE.md)** | Mobile voice P2P audio architecture |

---

## 🚀 Feature Guides

Learn how to use and extend specific features.

### Agent Development

| Document | Purpose |
|----------|---------|
| **[Agent Development Guide](guides/AGENT_DEVELOPMENT_GUIDE.md)** | Complete guide to creating and configuring agents |
| **[Tool Development Guide](guides/TOOL_DEVELOPMENT_GUIDE.md)** | Complete guide to creating custom tools |
| **[Multimodal Agent Guide](guides/MULTIMODAL_AGENT_GUIDE.md)** | Vision-capable agents that can see images |
| **[Dynamic Init Agent](guides/DYNAMIC_INIT_AGENT_IMPLEMENTATION.md)** | Custom agent initialization logic |
| **[Agent Description Injection](guides/DYNAMIC_AGENT_DESCRIPTION_INJECTION.md)** | Automatic orchestrator agent info |
| **[Database Agent Guide](guides/DATABASE_AGENT_GUIDE.md)** | MongoDB database management agent |
| **[API Agent Guide](guides/API_AGENT_GUIDE.md)** | Web API interaction agent |

### Voice System

| Document | Purpose |
|----------|---------|
| **[Mobile Voice Guide](guides/MOBILE_VOICE_GUIDE.md)** | Use smartphone as wireless microphone |
| **[Voice Assistant Integration](architecture/VOICE_ASSISTANT_INTEGRATION_PLAN.md)** | Voice system architecture and design |

### UI/UX Features

| Document | Purpose |
|----------|---------|
| **[Keyboard Navigation](guides/KEYBOARD_NAVIGATION_GUIDE.md)** | Keyboard shortcuts and accessibility |
| **[TV Navigation](guides/TV_NAVIGATION_GUIDE.md)** | TV remote control navigation |
| **[Spatial Navigation](guides/SPATIAL_NAVIGATION_GUIDE.md)** | Arrow key navigation system |

---

## 🔧 Deployment & Operations

Set up, deploy, and maintain the system.

| Document | Purpose |
|----------|---------|
| **[Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)** | Complete installation steps |
| **[Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)** | Step-by-step deployment verification |
| **[Jetson Deployment](deployment/JETSON_DEPLOYMENT_GUIDE.md)** | Deploy to Jetson Nano home server |
| **[Jetson Operations](deployment/JETSON_OPERATIONS_GUIDE.md)** | Maintain and update Jetson server |
| **[Jetson Dependencies](deployment/JETSON_DEPENDENCY_FIXES.md)** | Fix ARM64 dependency issues |

---

## 🐛 Troubleshooting & Fixes

Solutions to common problems and debugging guides.

### Mobile Voice Issues

| Document | Purpose |
|----------|---------|
| **[Mobile Voice Fixes](troubleshooting/MOBILE_VOICE_FIXES.md)** | Audio playback and database issues |
| **[HTTPS Mobile Setup](troubleshooting/HTTPS_MOBILE_VOICE_FIX.md)** | Configure nginx for HTTPS WebRTC |
| **[Mobile Voice Debugging](troubleshooting/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md)** | ADB debugging workflow |
| **[Echo Fix](troubleshooting/DESKTOP_SPEAKER_MUTE_FIX.md)** | Desktop speaker mute and echo elimination |
| **[Continuous Voice Fix](troubleshooting/CONTINUOUS_VOICE_FIX.md)** | Buffer size optimization for VAD |

### UI/Navigation Issues

| Document | Purpose |
|----------|---------|
| **[TV WebView Fix](troubleshooting/TV_WEBVIEW_FIX_SUMMARY.md)** | Nginx try_files with alias directive |
| **[URL Resolution Fix](troubleshooting/URL_FIX_IMPLEMENTATION.md)** | Centralized URL builder for all scenarios |
| **[Keyboard Navigation Fix](troubleshooting/KEYBOARD_NAVIGATION_FIX.md)** | Router context error resolution |

### Backend Issues

| Document | Purpose |
|----------|---------|
| **[Permission Fix](troubleshooting/PERMISSION_FIX_SUMMARY.md)** | Claude Code bypass permissions for voice |
| **[WebRTC Refactoring](troubleshooting/WEBRTC_REFACTORING_SUMMARY.md)** | Fix mobile voice connection issues |
| **[Screenshot Fix](troubleshooting/SCREENSHOT_FIX_GUIDE.md)** | Fix screenshot capture on GNOME Wayland |

---

## 📚 Reference Documentation

Technical references and implementation details.

### Code References

| Document | Purpose |
|----------|---------|
| **[Reference Code & Examples](references/README.md)** | AutoGen examples, legacy implementations, Jupyter notebooks |
| **[AutoGen Multimodality](guides/autogen-multimodality.md)** | Base64 images in AutoGen 0.5.5 |
| **[Screenshot Tool Guide](guides/SCREENSHOT_TOOL_README.md)** | Screenshot capture implementation |

### Reference Files

Located in [docs/references/](references/):
- **Python:** `AssistantAgent.py`, `memory.py`, `vectorstore.py`, `_code_executor_agent.py`
- **Notebooks:** `group-chat.ipynb`, `selector-group-chat.ipynb`, `multimodality-images.ipynb`, `termination.ipynb`
- **Migration:** `autogen_migration-guide.txt` (v0.2 to v0.4)

---

## 🗄️ Archive

Historical documents kept for reference (may be outdated).

| Document | Purpose | Status |
|----------|---------|--------|
| **[Documentation Audit](archive/DOCUMENTATION_AUDIT_SUMMARY.md)** | 2025-11-30 documentation review | Historical |
| **[Organization Summary](archive/ORGANIZATION_SUMMARY.md)** | 2025-10-11 refactoring | Historical |
| **[Session Summaries](../debug/)** | Debug session logs | Historical |

---

## 📝 How to Use This Index

1. **New to the project?** Start with [README.md](../README.md) and [CLAUDE.md](../CLAUDE.md)
2. **Setting up a deployment?** Go to [Deployment Guide](deployment/DEPLOYMENT_GUIDE.md)
3. **Building a feature?** Check Architecture & Feature Guides sections
4. **Debugging an issue?** Search the Troubleshooting section
5. **Understanding the codebase?** Read [Developer Guide](guides/DEVELOPER_GUIDE.md)

---

## 🔍 Quick Search

**By Topic:**
- **Agents:** Multimodal, Dynamic Init, Database, API Agent guides
- **Voice:** Mobile Voice, Voice Assistant Integration, WebRTC Architecture
- **Deployment:** Deployment Guide, Jetson Deployment, Jetson Operations
- **UI/UX:** Keyboard Nav, TV Nav, Spatial Nav
- **Troubleshooting:** Mobile Voice, TV WebView, URL Resolution

**By Task:**
- **Create new agent:** See Agent Development section
- **Deploy to production:** See Deployment & Operations section
- **Fix mobile voice:** See Mobile Voice Issues section
- **Debug navigation:** See UI/Navigation Issues section

---

## 📌 Document Maintenance

When adding new documentation:
1. Place in appropriate category folder (guides/, architecture/, deployment/, troubleshooting/)
2. Add entry to this index in the relevant section
3. Update CLAUDE.md if it's a critical reference document
4. Consider whether any existing docs should be archived

**Categories:**
- `guides/` - Feature-specific guides and how-tos
- `architecture/` - System design and technical architecture
- `deployment/` - Installation, deployment, operations
- `troubleshooting/` - Bug fixes, debugging guides, solutions
- `archive/` - Outdated or historical documents
