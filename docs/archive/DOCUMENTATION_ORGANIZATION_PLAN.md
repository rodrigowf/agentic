# Documentation Organization Plan

**Created:** 2025-11-30
**Status:** Proposed

This document provides a comprehensive analysis of the current documentation state and recommendations for improving organization, clarity, and usability.

---

## Executive Summary

**Current State:**
- **80 documentation files** across the project (excluding dependencies)
- Documentation scattered across 4 primary locations
- Mix of up-to-date and outdated content
- Some redundancy and overlap
- Inconsistent naming conventions

**Key Findings:**
- ✅ **Well-organized**: Backend tests/, scripts/, and core docs
- ✅ **Excellent**: Main guides (CLAUDE.md, README.md) are comprehensive
- ⚠️ **Needs attention**: Deployment docs have some redundancy
- ⚠️ **Cleanup needed**: Debug/ directory has many session-specific docs
- ⚠️ **Legacy content**: Some old planning docs in docs/

**Overall Assessment:** 7/10 - Good foundation, needs refinement

---

## Current Documentation Structure

### Primary Documentation Locations

```
agentic/
├── / (root)                     # 15 files - Main guides + legacy
│   ├── CLAUDE.md                # ⭐ Primary dev guide (2,418 lines)
│   ├── README.md                # ⭐ Project overview (1,861 lines)
│   ├── INDEX.md                 # ⭐ Quick navigation
│   ├── PROJECT_STRUCTURE.md     # ⭐ File organization
│   ├── ORGANIZATION_SUMMARY.md  # Recent reorganization
│   └── ... (legacy files)
│
├── docs/                        # 25 files - Project-wide docs
│   ├── DEPLOYMENT_INDEX.md      # ⭐ Deployment navigation
│   ├── DEPLOYMENT_GUIDE.md      # ⭐ Comprehensive deployment
│   ├── JETSON_DEPLOYMENT_GUIDE.md # ⭐ Jetson-specific deployment
│   ├── JETSON_OPERATIONS_GUIDE.md # ⭐ Server operations
│   ├── MOBILE_VOICE_GUIDE.md    # ⭐ Mobile interface guide
│   ├── WEBRTC_MOBILE_VOICE_ARCHITECTURE.md # ⭐ WebRTC architecture
│   ├── DYNAMIC_INIT_AGENT_IMPLEMENTATION.md # ⭐ Agent type guide
│   ├── FRONTEND_REFACTORING.md  # Architecture notes
│   ├── REFACTORING_SUMMARY.md   # Backend refactoring
│   ├── DEVELOPER_GUIDE.md       # Alternative dev guide (partial)
│   └── ... (planning docs, instructions)
│
├── backend/docs/                # 6 files - Backend-specific
│   ├── MULTIMODAL_AGENT_GUIDE.md # ⭐ Vision agent guide
│   ├── MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md
│   ├── SCREENSHOT_FIX_GUIDE.md  # Screenshot troubleshooting
│   ├── SCREENSHOT_TESTING_REPORT.md
│   ├── SCREENSHOT_TEST_SUMMARY.md
│   └── SCREENSHOT_TOOL_README.md
│
├── backend/tests/README.md      # ⭐ Test documentation
├── backend/scripts/README.md    # ⭐ Script documentation
│
└── debug/                       # 11 files - Debug & session notes
    ├── AUTOMATED_UI_DEVELOPMENT.md # ⭐ Screenshot workflow
    ├── MOBILE_VOICE_FIXES.md    # Mobile voice debugging
    ├── MOBILE_VOICE_DEBUG_GUIDE.md
    ├── MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md
    ├── HTTPS_MOBILE_VOICE_FIX.md
    ├── SESSION_SUMMARY_2025-11-29.md
    ├── CONTINUOUS_VOICE_FIX.md
    ├── DESKTOP_SPEAKER_MUTE_FIX.md
    ├── INACTIVE_CONVERSATION_CLEANUP.md
    ├── MOBILE_MIC_FIX_SUMMARY.md
    └── VOICE_IMPROVEMENTS_SUMMARY.md
```

### Documentation Categories by Purpose

**1. Primary Guides (Must-Read)** ⭐
- CLAUDE.md - Main development guide
- README.md - Project overview
- INDEX.md - Quick navigation
- PROJECT_STRUCTURE.md - File organization

**2. Deployment Documentation**
- DEPLOYMENT_INDEX.md - Navigation hub
- DEPLOYMENT_GUIDE.md - Comprehensive guide
- DEPLOYMENT_CHECKLIST.md - Verification steps
- JETSON_DEPLOYMENT_GUIDE.md - Jetson-specific
- JETSON_OPERATIONS_GUIDE.md - Server operations
- DEPLOYMENT_README.md - Quick start (root)

**3. Feature Documentation**
- MOBILE_VOICE_GUIDE.md - Mobile interface
- WEBRTC_MOBILE_VOICE_ARCHITECTURE.md - WebRTC design
- DYNAMIC_INIT_AGENT_IMPLEMENTATION.md - Agent types
- MULTIMODAL_AGENT_GUIDE.md - Vision agents
- TV_NAVIGATION_GUIDE.md - TV interface
- VOICE_ASSISTANT_INTEGRATION_PLAN.md - Voice system

**4. Architecture & Refactoring**
- FRONTEND_REFACTORING.md - Frontend organization
- REFACTORING_SUMMARY.md - Backend reorganization
- ORGANIZATION_SUMMARY.md - Project organization
- WEBRTC_REFACTORING_SUMMARY.md - WebRTC refactor
- DEVELOPER_GUIDE.md - Alternative dev guide

**5. Debug & Troubleshooting**
- AUTOMATED_UI_DEVELOPMENT.md - Screenshot workflow
- SCREENSHOT_FIX_GUIDE.md - Screenshot issues
- MOBILE_VOICE_FIXES.md - Mobile debugging
- HTTPS_MOBILE_VOICE_FIX.md - HTTPS setup
- backend/docs/SCREENSHOT_*.md - Screenshot docs

**6. Session Notes & Fixes**
- SESSION_SUMMARY_2025-11-29.md
- MOBILE_MIC_FIX_SUMMARY.md
- CONTINUOUS_VOICE_FIX.md
- DESKTOP_SPEAKER_MUTE_FIX.md
- VOICE_IMPROVEMENTS_SUMMARY.md
- INACTIVE_CONVERSATION_CLEANUP.md

**7. Legacy/Planning Documents**
- instructions-from-gpt.md
- nested_instructions.md
- enhance_chat.md
- enhancements_gpt-research.md
- deepresearch_enhancements_instructions.md
- autogen-multimodality.md
- autogen_migration-guide.txt
- AGENT_SELECTION_ANALYSIS.md
- URL_FIX_IMPLEMENTATION.md
- URL_RESOLUTION_STRATEGY.md

**8. Root-level Legacy Files**
- HTTPS_MOBILE_SETUP.md (duplicate/outdated?)
- MOBILE_VOICE_FIX_SUMMARY.md (should be in debug/)
- MOBILE_VOICE_DEBUGGING_LOG.md (should be in debug/)
- FINAL_FIX_AUDIO_OVERLAP.md (should be in debug/)
- DEPLOYMENT_README.md (should be in docs/)
- tasklist.md (active task list)
- files_todo.txt (legacy?)
- todo.txt (legacy?)

---

## Issues Identified

### 1. Redundancy & Overlap

**Deployment Documentation** (6 files covering similar topics):
- DEPLOYMENT_README.md (root) - Quick start
- DEPLOYMENT_GUIDE.md (docs/) - Comprehensive
- DEPLOYMENT_INDEX.md (docs/) - Navigation
- DEPLOYMENT_CHECKLIST.md (docs/) - Verification
- JETSON_DEPLOYMENT_GUIDE.md (docs/) - Jetson-specific
- JETSON_OPERATIONS_GUIDE.md (docs/) - Operations

**Recommendation:** Consolidate into clear hierarchy:
1. DEPLOYMENT_INDEX.md → Entry point
2. DEPLOYMENT_QUICK_START.md → 5-minute setup
3. DEPLOYMENT_COMPREHENSIVE.md → Full guide
4. DEPLOYMENT_JETSON.md → Jetson-specific
5. Remove DEPLOYMENT_README.md from root (move content to docs/)

**Mobile Voice Documentation** (7 files):
- MOBILE_VOICE_GUIDE.md (docs/) - Main guide
- MOBILE_VOICE_FIXES.md (debug/) - Fixes
- MOBILE_VOICE_DEBUG_GUIDE.md (debug/) - Debugging
- MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md (debug/) - HTTPS debug
- HTTPS_MOBILE_VOICE_FIX.md (debug/) - HTTPS fix
- MOBILE_VOICE_FIX_SUMMARY.md (root) - Summary
- MOBILE_VOICE_DEBUGGING_LOG.md (root) - Log

**Recommendation:** Consolidate:
1. Keep MOBILE_VOICE_GUIDE.md in docs/ (main reference)
2. Create docs/MOBILE_VOICE_TROUBLESHOOTING.md (merge debug guides)
3. Archive SESSION_SUMMARY files to archive/sessions/
4. Move root-level files to debug/ or archive/

**Screenshot Documentation** (6 files in backend/docs/):
- SCREENSHOT_FIX_GUIDE.md
- SCREENSHOT_TESTING_REPORT.md
- SCREENSHOT_TEST_SUMMARY.md
- SCREENSHOT_TOOL_README.md
- MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md
- (Plus AUTOMATED_UI_DEVELOPMENT.md in debug/)

**Recommendation:**
1. Consolidate testing reports into single SCREENSHOT_TESTING.md
2. Keep FIX_GUIDE and TOOL_README separate
3. Create backend/docs/IMAGE_TOOLS.md (merge screenshot + multimodal)

### 2. Misplaced Files

**Files that should be in docs/**:
- DEPLOYMENT_README.md (root → docs/DEPLOYMENT_QUICK_START.md)
- HTTPS_MOBILE_SETUP.md (root → docs/ or debug/)

**Files that should be in debug/**:
- MOBILE_VOICE_FIX_SUMMARY.md (root → debug/)
- MOBILE_VOICE_DEBUGGING_LOG.md (root → debug/)
- FINAL_FIX_AUDIO_OVERLAP.md (root → debug/)

**Files that should be archived**:
- files_todo.txt (root → archive/)
- todo.txt (root → archive/ or delete if completed)
- Session summary files older than 3 months

### 3. Legacy/Outdated Content

**Planning Documents (docs/):**
- instructions-from-gpt.md - Old planning
- nested_instructions.md - Old implementation notes
- enhance_chat.md - Old feature planning
- enhancements_gpt-research.md - Old planning
- deepresearch_enhancements_instructions.md - Old planning
- autogen-multimodality.md - Superseded by MULTIMODAL_AGENT_GUIDE.md
- autogen_migration-guide.txt - Old migration notes

**Recommendation:** Create `docs/archive/planning/` and move these files

**Fix Summaries (debug/):**
Many session-specific fix summaries that are no longer actively referenced.

**Recommendation:** Create `debug/archive/sessions/` for historical records

### 4. Naming Inconsistencies

**Current Mix:**
- ALL_CAPS.md (most guides)
- lowercase-with-hyphens.md (some legacy)
- camelCase.md (rare)

**Recommendation:** Standardize to ALL_CAPS.md for consistency

### 5. Missing Documentation

**Gaps Identified:**
1. ❌ No single "Getting Started" guide (README is very long)
2. ❌ No API reference documentation (mentioned in README, not created)
3. ❌ No architecture diagrams (text-only)
4. ❌ No contribution guidelines
5. ❌ No changelog/release notes
6. ❌ No testing strategy guide
7. ❌ No security documentation

---

## Recommended Organization Structure

```
agentic/
│
├── /                            # Root - Essential files only
│   ├── README.md                # Project overview (keep)
│   ├── CLAUDE.md                # Primary dev guide (keep)
│   ├── INDEX.md                 # Quick navigation (keep)
│   ├── QUICKSTART.md            # NEW: 5-minute getting started
│   ├── CHANGELOG.md             # NEW: Version history
│   ├── CONTRIBUTING.md          # NEW: Contribution guide
│   ├── PROJECT_STRUCTURE.md     # File organization (keep)
│   ├── tasklist.md              # Active tasks (keep if active)
│   └── ... (config files only)
│
├── docs/                        # Project-wide documentation
│   │
│   ├── README.md                # NEW: Docs navigation
│   ├── DOCUMENTATION_INDEX.md   # NEW: Complete doc catalog
│   │
│   ├── getting-started/         # NEW: Getting started guides
│   │   ├── INSTALLATION.md
│   │   ├── FIRST_AGENT.md
│   │   ├── FIRST_TOOL.md
│   │   └── COMMON_ISSUES.md
│   │
│   ├── deployment/              # NEW: Deployment docs consolidated
│   │   ├── README.md            # Navigation
│   │   ├── QUICK_START.md       # 5-minute deploy
│   │   ├── COMPREHENSIVE.md     # Full deployment guide
│   │   ├── JETSON.md            # Jetson deployment
│   │   ├── JETSON_OPERATIONS.md # Server operations
│   │   ├── CHECKLIST.md         # Verification
│   │   └── PRODUCTION.md        # Production hardening
│   │
│   ├── features/                # NEW: Feature documentation
│   │   ├── VOICE_ASSISTANT.md   # Voice system
│   │   ├── MOBILE_VOICE.md      # Mobile interface
│   │   ├── WEBRTC_ARCHITECTURE.md # WebRTC design
│   │   ├── CLAUDE_CODE.md       # Self-editing
│   │   ├── MEMORY_SYSTEM.md     # Memory tools
│   │   └── TV_INTERFACE.md      # TV navigation
│   │
│   ├── agents/                  # NEW: Agent documentation
│   │   ├── AGENT_TYPES.md       # Overview
│   │   ├── LOOPING_AGENTS.md
│   │   ├── NESTED_TEAMS.md
│   │   ├── MULTIMODAL_AGENTS.md # Vision agents
│   │   ├── DYNAMIC_INIT.md      # Dynamic initialization
│   │   └── CREATING_AGENTS.md   # Step-by-step guide
│   │
│   ├── tools/                   # NEW: Tool documentation
│   │   ├── TOOL_SYSTEM.md       # Overview
│   │   ├── CREATING_TOOLS.md
│   │   ├── BUILT_IN_TOOLS.md
│   │   └── TOOL_EXAMPLES.md
│   │
│   ├── architecture/            # NEW: Architecture docs
│   │   ├── OVERVIEW.md
│   │   ├── BACKEND.md
│   │   ├── FRONTEND.md
│   │   ├── WEBSOCKET_PROTOCOL.md
│   │   ├── EVENT_SYSTEM.md
│   │   └── DATA_FLOW.md
│   │
│   ├── troubleshooting/         # NEW: Debugging & fixes
│   │   ├── COMMON_ISSUES.md
│   │   ├── MOBILE_VOICE.md
│   │   ├── SCREENSHOT_ISSUES.md
│   │   ├── WEBRTC_DEBUGGING.md
│   │   └── BACKEND_ERRORS.md
│   │
│   ├── api/                     # NEW: API documentation
│   │   ├── REST_API.md
│   │   ├── WEBSOCKET_API.md
│   │   └── OPENAPI_SPEC.json
│   │
│   ├── refactoring/             # Reorganization notes
│   │   ├── BACKEND_REFACTORING.md
│   │   ├── FRONTEND_REFACTORING.md
│   │   ├── WEBRTC_REFACTORING.md
│   │   └── ORGANIZATION_2025-10-11.md
│   │
│   └── archive/                 # Historical documents
│       ├── planning/            # Old planning docs
│       └── sessions/            # Session summaries
│
├── backend/
│   ├── docs/                    # Backend-specific docs
│   │   ├── README.md            # Backend docs index
│   │   ├── TESTING.md           # Testing guide
│   │   ├── IMAGE_TOOLS.md       # Screenshots + multimodal
│   │   └── CODE_STRUCTURE.md    # Backend architecture
│   │
│   ├── tests/README.md          # Test documentation (keep)
│   └── scripts/README.md        # Script documentation (keep)
│
├── frontend/
│   └── docs/                    # NEW: Frontend docs
│       ├── README.md
│       ├── COMPONENT_GUIDE.md
│       ├── FEATURE_STRUCTURE.md
│       └── TESTING.md
│
└── debug/                       # Debug tools & recent fixes
    ├── README.md                # NEW: Debug tools guide
    ├── SCREENSHOT_WORKFLOW.md   # UI development workflow
    ├── VOICE_DEBUGGING.md       # Voice troubleshooting
    ├── HTTPS_SETUP.md           # HTTPS mobile setup
    │
    └── archive/                 # Historical fixes
        └── sessions/            # Old session summaries
            └── 2025-11/
                └── SESSION_2025-11-29.md
```

---

## Consolidation Recommendations

### Phase 1: Immediate Cleanup (High Impact)

**1. Move Misplaced Files**
```bash
# Move to docs/
mv DEPLOYMENT_README.md docs/deployment/QUICK_START.md
mv HTTPS_MOBILE_SETUP.md docs/troubleshooting/MOBILE_HTTPS.md

# Move to debug/
mv MOBILE_VOICE_FIX_SUMMARY.md debug/
mv MOBILE_VOICE_DEBUGGING_LOG.md debug/
mv FINAL_FIX_AUDIO_OVERLAP.md debug/

# Archive legacy
mkdir -p docs/archive/planning
mv docs/instructions-from-gpt.md docs/archive/planning/
mv docs/nested_instructions.md docs/archive/planning/
mv docs/enhance_chat.md docs/archive/planning/
mv docs/enhancements_gpt-research.md docs/archive/planning/
mv docs/deepresearch_enhancements_instructions.md docs/archive/planning/
mv docs/autogen-multimodality.md docs/archive/planning/
mv docs/autogen_migration-guide.txt docs/archive/planning/
mv docs/AGENT_SELECTION_ANALYSIS.md docs/archive/planning/
mv docs/URL_FIX_IMPLEMENTATION.md docs/archive/planning/
mv docs/URL_RESOLUTION_STRATEGY.md docs/archive/planning/
```

**2. Create Directory Structure**
```bash
mkdir -p docs/{getting-started,deployment,features,agents,tools,architecture,troubleshooting,api,refactoring,archive/sessions}
mkdir -p frontend/docs
mkdir -p debug/archive/sessions/2025-11
```

**3. Archive Session Summaries**
```bash
mv debug/SESSION_SUMMARY_2025-11-29.md debug/archive/sessions/2025-11/
mv debug/MOBILE_MIC_FIX_SUMMARY.md debug/archive/sessions/2025-11/
mv debug/CONTINUOUS_VOICE_FIX.md debug/archive/sessions/2025-11/
mv debug/DESKTOP_SPEAKER_MUTE_FIX.md debug/archive/sessions/2025-11/
mv debug/VOICE_IMPROVEMENTS_SUMMARY.md debug/archive/sessions/2025-11/
mv debug/INACTIVE_CONVERSATION_CLEANUP.md debug/archive/sessions/2025-11/
```

### Phase 2: Consolidate Documentation

**1. Deployment Docs**
- Merge into docs/deployment/ hierarchy
- Create clear navigation README.md
- Remove redundant content

**2. Mobile Voice Docs**
- Consolidate 7 files into 2-3 focused docs
- Main guide + troubleshooting guide
- Archive session-specific notes

**3. Screenshot Docs**
- Merge testing reports
- Create single IMAGE_TOOLS.md
- Keep troubleshooting separate

### Phase 3: Create Missing Documentation

**1. Quick Start Guide** (docs/QUICKSTART.md)
- 5-minute setup
- First agent
- First tool
- Voice interface

**2. API Documentation** (docs/api/)
- REST API reference
- WebSocket protocol
- Event types
- OpenAPI spec

**3. Architecture Diagrams** (docs/architecture/)
- System overview
- Data flow
- Component interaction
- Use PlantUML or Mermaid

**4. Testing Guide** (backend/docs/TESTING.md)
- Testing strategy
- Writing tests
- Running tests
- CI/CD integration

### Phase 4: Standardization

**1. Naming Convention**
- Rename all guides to ALL_CAPS.md
- Use hyphens for multi-word (MOBILE-VOICE.md)
- Consistent prefixes by category

**2. Front Matter**
- Add standard header to all docs:
  ```markdown
  # Document Title
  **Last Updated:** YYYY-MM-DD
  **Status:** Active | Archived | Superseded
  **Replaces:** [old-doc.md]
  ```

**3. Cross-References**
- Audit all internal links
- Update to new paths
- Create navigation headers
- Add "See also" sections

---

## Priority Actions

### Immediate (This Week)

1. ✅ **Create this plan** - DONE
2. 🔴 **Move misplaced files** - High impact, low effort
3. 🔴 **Archive legacy planning docs** - Reduce clutter
4. 🔴 **Archive session summaries** - Organize debug/
5. 🟡 **Create QUICKSTART.md** - Improve onboarding

### Short-term (Next Sprint)

6. 🟡 **Consolidate deployment docs** - Remove redundancy
7. 🟡 **Consolidate mobile voice docs** - Streamline troubleshooting
8. 🟡 **Create docs directory structure** - Prepare for reorganization
9. 🟡 **Create README.md in each new directory** - Navigation

### Medium-term (Next Month)

10. 🟢 **Reorganize into feature-based structure** - Scalability
11. 🟢 **Create API documentation** - Developer experience
12. 🟢 **Add architecture diagrams** - Visual understanding
13. 🟢 **Create testing guide** - Best practices

### Long-term (Ongoing)

14. 🔵 **Maintain changelog** - Version tracking
15. 🔵 **Regular review and archival** - Prevent bloat
16. 🔵 **Update cross-references** - Keep links valid
17. 🔵 **Collect feedback** - Continuous improvement

---

## Success Metrics

### Quantitative
- ✅ Reduce redundant docs by 30% (25 → 17 active files)
- ✅ Move 100% of misplaced files to correct locations
- ✅ Archive 100% of legacy planning docs
- ✅ Create navigation README in each new directory
- ✅ Reduce average time to find documentation by 50%

### Qualitative
- ✅ Clear navigation from any entry point
- ✅ No more than 3 clicks to any documentation
- ✅ Consistent naming and structure
- ✅ Up-to-date content with maintenance dates
- ✅ Easy onboarding for new developers

---

## Maintenance Plan

### Ongoing Responsibilities

**When Adding New Documentation:**
1. Choose appropriate directory
2. Follow naming convention
3. Add front matter with date
4. Update relevant navigation READMEs
5. Update INDEX.md or DOCUMENTATION_INDEX.md
6. Cross-reference related docs

**Monthly Reviews:**
1. Check for outdated content
2. Archive session summaries >3 months old
3. Verify all links are valid
4. Update "Last Updated" dates on modified docs
5. Consolidate new troubleshooting docs

**Quarterly Reviews:**
1. Assess documentation coverage
2. Identify gaps
3. Consolidate redundant docs
4. Update architecture docs
5. Review and update QUICKSTART.md

---

## Implementation Checklist

### Phase 1: Immediate Cleanup ✅
- [ ] Create archive directories
- [ ] Move misplaced root files to docs/
- [ ] Move misplaced root files to debug/
- [ ] Archive legacy planning docs
- [ ] Archive session summaries
- [ ] Clean up root directory

### Phase 2: Consolidation
- [ ] Create docs/ subdirectories
- [ ] Consolidate deployment docs
- [ ] Consolidate mobile voice docs
- [ ] Consolidate screenshot docs
- [ ] Create navigation READMEs

### Phase 3: New Documentation
- [ ] Write QUICKSTART.md
- [ ] Create API documentation
- [ ] Create architecture docs with diagrams
- [ ] Create testing guide
- [ ] Create CHANGELOG.md
- [ ] Create CONTRIBUTING.md

### Phase 4: Standardization
- [ ] Standardize all file names
- [ ] Add front matter to all docs
- [ ] Audit and fix all cross-references
- [ ] Create DOCUMENTATION_INDEX.md
- [ ] Update INDEX.md with new structure

### Phase 5: Verification
- [ ] Test all documentation links
- [ ] Verify navigation from entry points
- [ ] Get feedback from team
- [ ] Update CLAUDE.md with new structure
- [ ] Update PROJECT_STRUCTURE.md

---

## Migration Guide for Developers

### Finding Documentation After Reorganization

**Before:**
```
Where is the deployment guide?
- DEPLOYMENT_README.md (root)
- docs/DEPLOYMENT_GUIDE.md
- docs/DEPLOYMENT_INDEX.md
```

**After:**
```
Where is the deployment guide?
1. Start at docs/deployment/README.md
2. Choose:
   - QUICK_START.md (5 minutes)
   - COMPREHENSIVE.md (full guide)
   - JETSON.md (Jetson-specific)
```

**Before:**
```
How do I debug mobile voice?
- Check 7 different files across root/debug/docs
```

**After:**
```
How do I debug mobile voice?
1. docs/troubleshooting/MOBILE_VOICE.md
2. Or: docs/features/MOBILE_VOICE.md (feature guide)
```

### Updated References

All documentation will include a migration note for 3 months:

```markdown
> **Note:** This documentation was reorganized on 2025-11-30.
> Previous location: `docs/MOBILE_VOICE_GUIDE.md`
> New location: `docs/features/MOBILE_VOICE.md`
```

---

## Conclusion

This plan provides a clear path to improve documentation organization while maintaining backward compatibility during migration. The proposed structure is:

1. **Scalable** - Easy to add new docs in correct category
2. **Navigable** - Clear hierarchy and navigation
3. **Maintainable** - Regular review processes
4. **User-friendly** - Fast time-to-documentation
5. **Professional** - Industry-standard organization

### Next Steps

1. **Review this plan** with the team
2. **Prioritize actions** based on team feedback
3. **Implement Phase 1** (immediate cleanup)
4. **Iterate and improve** based on results

---

**Created:** 2025-11-30
**Status:** Proposed - Awaiting Review
**Estimated Effort:** 8-12 hours total (across all phases)
**ROI:** High - Significantly improves developer experience
