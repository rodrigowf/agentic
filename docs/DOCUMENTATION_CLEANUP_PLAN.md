# Documentation Cleanup Plan

**Date:** 2025-12-05
**Status:** Ready for execution
**Purpose:** Organize, consolidate, and update all WebRTC/voice documentation

---

## Current State Analysis

### Architecture Status ✅
- **Active:** Pure WebRTC bridge (Browser ↔ Backend ↔ OpenAI)
- **Backend:** FastAPI + aiortc + OpenAI Realtime API
- **Frontend:** VoiceAssistantModular.js using useBackendWebRTC hook
- **Integrations:** Nested agents + Claude Code via WebSocket
- **Deprecated:** All Pipecat implementations removed

### Documentation Issues

**Problem 1: Pipecat References (OBSOLETE)**
All Pipecat-related docs are now obsolete since migration to pure WebRTC:
- Backend files deleted: `realtime_voice_pipecat*.py`
- Frontend hooks deleted: `usePipecatWebSocket.js`
- Test files: `test_pipecat_*.py`, `e2e_voice_pipecat_simple.spec.js`

**Problem 2: Scattered Documentation**
10+ markdown files about WebRTC with overlapping content:
- `WEBRTC_*.md` (7 files in root)
- `docs/WEBRTC_*.md` (3 files)
- `docs/architecture/WEBRTC_*.md` (2 files)

**Problem 3: Outdated References**
- `CLAUDE.md` references non-existent guides
- Old mobile voice debugging docs (HTTPS issues now fixed)
- References to deprecated voice pages

---

## Proposed Organization

### Tier 1: Essential Guides (Keep & Update)

**Location:** `/home/rodrigo/agentic/docs/voice/`

1. **`VOICE_SYSTEM_OVERVIEW.md`** (NEW - consolidate)
   - Architecture diagram
   - Data flow
   - Key components
   - Integration points
   - **Sources:** Consolidate from `WEBRTC_ARCHITECTURE_FILES.md`, `WEBRTC_NESTED_INTEGRATION.md`, `webrtc-bridge-notes.md`

2. **`VOICE_QUICK_START.md`** (MOVE + UPDATE)
   - **From:** `/WEBRTC_QUICK_START.md`
   - **To:** `/docs/voice/VOICE_QUICK_START.md`
   - Update URLs and paths

3. **`VOICE_INTERACTIVE_GUIDE.md`** (MOVE + UPDATE)
   - **From:** `/INTERACTIVE_SESSION_GUIDE.md`
   - **To:** `/docs/voice/VOICE_INTERACTIVE_GUIDE.md`
   - Comprehensive testing walkthrough

4. **`VOICE_COMMANDS.md`** (MOVE + UPDATE)
   - **From:** `/WEBRTC_COMMANDS.md`
   - **To:** `/docs/voice/VOICE_COMMANDS.md`
   - Command reference

5. **`VOICE_TROUBLESHOOTING.md`** (NEW - consolidate)
   - Common issues and fixes
   - Debug procedures
   - Performance tuning
   - **Sources:** Extract from multiple guides

### Tier 2: Technical Documentation (Keep)

**Location:** `/home/rodrigo/agentic/docs/voice/technical/`

1. **`BACKEND_IMPLEMENTATION.md`** (NEW)
   - `realtime_voice_webrtc.py` architecture
   - `openai_webrtc_client.py` details
   - WebSocket integration
   - Tool execution

2. **`FRONTEND_IMPLEMENTATION.md`** (NEW)
   - VoiceAssistantModular.js structure
   - useBackendWebRTC hook
   - Component hierarchy
   - State management

3. **`NESTED_AGENTS_INTEGRATION.md`** (MOVE)
   - **From:** `/WEBRTC_NESTED_INTEGRATION.md`
   - **To:** `/docs/voice/technical/NESTED_AGENTS_INTEGRATION.md`
   - Keep as-is (already excellent)

4. **`AUDIO_FIXES_LOG.md`** (NEW - consolidate)
   - Historical audio issues and fixes
   - Sample rate corrections
   - Browser audio forwarding fix
   - **Sources:** `WEBRTC_AUDIO_FIX_2025_12_04.md`, `AUDIO_FIX_SUMMARY.md`, etc.

### Tier 3: Archive (Move to docs/archive)

**Location:** `/home/rodrigo/agentic/docs/archive/voice/`

**Move these files:**
1. `WEBRTC_NESTED_COMPLETE.md` - Milestone marker
2. `README_WEBRTC_SESSION.md` - Superseded by Quick Start
3. `docs/WEBRTC_INTERACTIVE_TESTING.md` - Superseded by Interactive Guide
4. All Pipecat documentation (if any remains)
5. Old mobile voice debugging guides (issues resolved)

### Tier 4: Delete (Obsolete)

**Remove completely:**
1. Pipecat test files:
   - `backend/tests/test_pipecat_websocket_e2e.py`
   - `backend/tests/unit/test_pipecat_controller.py`
   - `tests/e2e_voice_pipecat_simple.spec.js`
   - `backend/api/__pycache__/realtime_voice_pipecat*.pyc`

2. Temporary fix notes (content integrated):
   - `WEBRTC_AUDIO_FIX_2025_12_04.md` (integrate → AUDIO_FIXES_LOG.md)
   - Individual fix summary files

---

## Updated Directory Structure

```
/home/rodrigo/agentic/
├── CLAUDE.md                                    # Updated with correct references
├── docs/
│   ├── DOCUMENTATION_INDEX.md                   # Updated master index
│   ├── voice/                                   # NEW - Voice system docs
│   │   ├── VOICE_SYSTEM_OVERVIEW.md            # Architecture & integration
│   │   ├── VOICE_QUICK_START.md                # 5-min setup
│   │   ├── VOICE_INTERACTIVE_GUIDE.md          # Complete walkthrough
│   │   ├── VOICE_COMMANDS.md                   # Command reference
│   │   ├── VOICE_TROUBLESHOOTING.md            # Debug guide
│   │   └── technical/
│   │       ├── BACKEND_IMPLEMENTATION.md       # Backend details
│   │       ├── FRONTEND_IMPLEMENTATION.md      # Frontend details
│   │       ├── NESTED_AGENTS_INTEGRATION.md    # Agent integration
│   │       └── AUDIO_FIXES_LOG.md              # Historical fixes
│   ├── guides/
│   │   ├── MOBILE_VOICE_GUIDE.md               # Keep (mobile-specific)
│   │   └── ...                                  # Other guides
│   └── archive/
│       └── voice/                               # Archived voice docs
│           ├── WEBRTC_NESTED_COMPLETE.md
│           ├── README_WEBRTC_SESSION.md
│           └── ...
└── (Remove from root: WEBRTC_*.md files)
```

---

## CLAUDE.md Updates Required

### Current References (BROKEN)
```markdown
- **[WEBRTC_QUICK_START.md](WEBRTC_QUICK_START.md)** - 1-minute setup
- **[INTERACTIVE_SESSION_GUIDE.md](INTERACTIVE_SESSION_GUIDE.md)** - Full walkthrough
- **[WEBRTC_COMMANDS.md](WEBRTC_COMMANDS.md)** - Command reference
- **[docs/WEBRTC_INTERACTIVE_TESTING.md](docs/WEBRTC_INTERACTIVE_TESTING.md)** - Testing guide
```

### Corrected References
```markdown
### Voice System
- **[Voice System Overview](docs/voice/VOICE_SYSTEM_OVERVIEW.md)** - Architecture & integration
- **[Voice Quick Start](docs/voice/VOICE_QUICK_START.md)** - 5-minute setup
- **[Voice Interactive Guide](docs/voice/VOICE_INTERACTIVE_GUIDE.md)** - Complete walkthrough
- **[Voice Commands](docs/voice/VOICE_COMMANDS.md)** - Command reference
- **[Voice Troubleshooting](docs/voice/VOICE_TROUBLESHOOTING.md)** - Debug guide

### Technical Details
- **[Backend Implementation](docs/voice/technical/BACKEND_IMPLEMENTATION.md)** - WebRTC bridge architecture
- **[Frontend Implementation](docs/voice/technical/FRONTEND_IMPLEMENTATION.md)** - React components & hooks
- **[Nested Agents Integration](docs/voice/technical/NESTED_AGENTS_INTEGRATION.md)** - Agent orchestration
```

### Architecture Section Update
Replace scattered references with:
```markdown
## Voice Assistant Architecture

**Pure WebRTC Bridge:**
```
Browser ↔ Backend (aiortc) ↔ OpenAI Realtime API
   ↓           ↓
WebRTC    WebSocket (events)
          WebSocket (nested agents)
          WebSocket (Claude Code)
```

**Key Files:**
- Backend: `backend/api/realtime_voice_webrtc.py`, `openai_webrtc_client.py`
- Frontend: `frontend/src/features/voice/pages/VoiceAssistantModular.js`
- Hooks: `frontend/src/features/voice/hooks/useBackendWebRTC.js`

**Features:**
- Real-time bidirectional audio (PCM16 @ 48kHz)
- Server-side VAD (OpenAI)
- Whisper transcription
- Tool execution (5 tools: send_to_nested, send_to_claude_code, pause, reset, pause_claude_code)
- Event streaming & persistence (SQLite)
- Mobile support
```

---

## Implementation Checklist

### Phase 1: Create New Consolidated Docs ✅
- [ ] Create `docs/voice/` directory
- [ ] Write `VOICE_SYSTEM_OVERVIEW.md` (consolidate from 3 sources)
- [ ] Write `VOICE_TROUBLESHOOTING.md` (extract from multiple guides)
- [ ] Create `docs/voice/technical/` directory
- [ ] Write `BACKEND_IMPLEMENTATION.md`
- [ ] Write `FRONTEND_IMPLEMENTATION.md`
- [ ] Write `AUDIO_FIXES_LOG.md` (consolidate fix history)

### Phase 2: Move & Update Existing Docs ✅
- [ ] Move `WEBRTC_QUICK_START.md` → `docs/voice/VOICE_QUICK_START.md`
- [ ] Move `INTERACTIVE_SESSION_GUIDE.md` → `docs/voice/VOICE_INTERACTIVE_GUIDE.md`
- [ ] Move `WEBRTC_COMMANDS.md` → `docs/voice/VOICE_COMMANDS.md`
- [ ] Move `WEBRTC_NESTED_INTEGRATION.md` → `docs/voice/technical/NESTED_AGENTS_INTEGRATION.md`
- [ ] Update all internal cross-references in moved files

### Phase 3: Archive Old Docs ✅
- [ ] Create `docs/archive/voice/` directory
- [ ] Move milestone/completion docs to archive
- [ ] Move superseded guides to archive

### Phase 4: Delete Obsolete Files ✅
- [ ] Delete Pipecat test files
- [ ] Delete Pipecat .pyc files
- [ ] Delete temporary fix notes (after consolidating)
- [ ] Remove WEBRTC_*.md from root (after moving content)

### Phase 5: Update References ✅
- [ ] Update `CLAUDE.md` with new structure
- [ ] Update `docs/DOCUMENTATION_INDEX.md`
- [ ] Update `README.md` (if voice references exist)
- [ ] Search for broken links: `grep -r "WEBRTC_" docs/`

### Phase 6: Verify ✅
- [ ] All links resolve correctly
- [ ] No duplicate content
- [ ] All active code files referenced correctly
- [ ] Quick start guide works end-to-end

---

## Benefits

1. **Single Source of Truth** - One place for voice system docs
2. **Clear Hierarchy** - User guides → Technical docs → Archive
3. **No Duplication** - Consolidated overlapping content
4. **Easy Discovery** - Logical structure in `docs/voice/`
5. **Maintainable** - Clear ownership of each doc type
6. **Updated References** - CLAUDE.md points to correct locations

---

## Rollout Strategy

**Approach:** Big-bang migration (all at once)

**Rationale:**
- Prevents broken link period
- Clear before/after state
- Easier to verify completeness

**Steps:**
1. Create all new docs (don't delete old yet)
2. Move files to new locations
3. Update CLAUDE.md + DOCUMENTATION_INDEX.md
4. Archive old files
5. Delete obsolete files
6. Verify all links

**Rollback:** Keep git commit before cleanup for easy revert

---

## Next Steps

1. Execute Phase 1 (create new consolidated docs)
2. Execute Phase 2 (move & update existing)
3. Execute Phase 3 (archive)
4. Execute Phase 4 (delete obsolete)
5. Execute Phase 5 (update references)
6. Execute Phase 6 (verify)

**Estimated Time:** 2-3 hours total

---

**Status:** ✅ Plan Complete - Ready for Execution
