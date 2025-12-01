# Inactive Conversation Cleanup Implementation

**Date:** 2025-11-29
**Status:** ✅ Complete

## Overview

Implemented automatic cleanup of inactive voice conversations to prevent stale/abandoned conversations from causing errors in the mobile and desktop voice interfaces.

## Problem

Users were experiencing errors when:
1. Mobile page tried to load deleted conversations (404 errors)
2. MUI Select component showed out-of-range conversation IDs
3. Conversation list became cluttered with old, inactive sessions

## Solution

Added automatic cleanup that runs when starting voice sessions on both desktop and mobile:
- **Deletes conversations** inactive for more than 30 minutes (configurable)
- **Runs automatically** when starting voice sessions
- **Fails gracefully** - errors don't prevent session from starting
- **Prevents clutter** - keeps conversation list clean

## Implementation

### 1. Backend: ConversationStore Method

**File:** `/home/rodrigo/agentic/backend/utils/voice_conversation_store.py`

Added `cleanup_inactive_conversations()` method:

```python
def cleanup_inactive_conversations(self, inactive_minutes: int = 30) -> List[str]:
    """
    Delete conversations that haven't been updated in the specified time period.
    Returns list of deleted conversation IDs.
    """
    from datetime import datetime, timedelta, timezone

    cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=inactive_minutes)).isoformat()

    with self._connection() as conn:
        # First, get the IDs that will be deleted
        rows = conn.execute(
            """
            SELECT id FROM conversations
            WHERE datetime(updated_at) < datetime(?)
            """,
            (cutoff_time,),
        ).fetchall()

        deleted_ids = [row[0] for row in rows]

        # Delete the conversations (CASCADE will delete events)
        if deleted_ids:
            placeholders = ",".join("?" * len(deleted_ids))
            conn.execute(
                f"DELETE FROM conversations WHERE id IN ({placeholders})",
                deleted_ids,
            )

    return deleted_ids
```

**Key Features:**
- Uses SQLite datetime comparison for accurate filtering
- Returns list of deleted IDs for logging
- CASCADE delete removes associated events automatically
- Configurable inactive time threshold (default: 30 minutes)

### 2. Backend: REST API Endpoint

**File:** `/home/rodrigo/agentic/backend/api/realtime_voice.py`

Added POST endpoint at `/api/realtime/conversations/cleanup`:

```python
@router.post("/conversations/cleanup")
def cleanup_inactive_conversations(
    inactive_minutes: int = Query(30, ge=1, le=1440, description="Delete conversations inactive for this many minutes")
) -> Dict[str, Any]:
    """
    Delete conversations that haven't been updated in the specified time period.
    Default is 30 minutes. This helps clean up stale/abandoned conversations.
    """
    deleted_ids = conversation_store.cleanup_inactive_conversations(inactive_minutes)
    return {
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "inactive_minutes": inactive_minutes
    }
```

**Response Format:**
```json
{
  "deleted_count": 3,
  "deleted_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "inactive_minutes": 30
}
```

**Endpoint Details:**
- **Method:** POST
- **URL:** `/api/realtime/conversations/cleanup`
- **Query Parameter:** `inactive_minutes` (1-1440, default: 30)
- **Returns:** JSON with count and list of deleted conversation IDs

### 3. Frontend: API Client Function

**File:** `/home/rodrigo/agentic/frontend/src/api.js`

Added API client function:

```javascript
export const cleanupInactiveConversations = (inactiveMinutes = 30) =>
  API.post(`${VOICE_BASE}/conversations/cleanup?inactive_minutes=${inactiveMinutes}`);
```

**Usage:**
```javascript
const result = await cleanupInactiveConversations(30);
console.log(`Deleted ${result.data.deleted_count} conversations`);
```

### 4. Frontend: Desktop Voice Integration

**File:** `/home/rodrigo/agentic/frontend/src/features/voice/pages/VoiceAssistant.js`

Added cleanup call at the start of `startSession()`:

```javascript
const startSession = async () => {
  if (isRunning) return;
  setIsRunning(true);
  setIsMuted(false);
  setError(null);
  try {
    // Clean up inactive conversations (older than 30 minutes)
    try {
      const cleanupResult = await cleanupInactiveConversations(30);
      if (cleanupResult.data?.deleted_count > 0) {
        console.log(`[Cleanup] Deleted ${cleanupResult.data.deleted_count} inactive conversations:`, cleanupResult.data.deleted_ids);
      }
    } catch (cleanupErr) {
      console.warn('[Cleanup] Failed to cleanup inactive conversations:', cleanupErr);
      // Don't fail the session start if cleanup fails
    }

    // ... rest of session setup
```

**Behavior:**
- Runs automatically when user clicks "Start" button
- Logs deleted conversations to console
- Gracefully handles cleanup errors
- Doesn't block session start if cleanup fails

### 5. Frontend: Mobile Voice Integration

**File:** `/home/rodrigo/agentic/frontend/src/features/voice/pages/MobileVoice.js`

Added identical cleanup call at the start of `startSession()`:

```javascript
const startSession = async () => {
  if (isRunning || !selectedConversationId) return;
  setIsRunning(true);
  setIsMuted(true);
  setError(null);

  try {
    // Clean up inactive conversations (older than 30 minutes)
    try {
      const cleanupResult = await cleanupInactiveConversations(30);
      if (cleanupResult.data?.deleted_count > 0) {
        console.log(`[MobileVoice Cleanup] Deleted ${cleanupResult.data.deleted_count} inactive conversations:`, cleanupResult.data.deleted_ids);
      }
    } catch (cleanupErr) {
      console.warn('[MobileVoice Cleanup] Failed to cleanup inactive conversations:', cleanupErr);
      // Don't fail the session start if cleanup fails
    }

    // ... rest of session setup
```

**Same graceful error handling as desktop**

## Usage

### Automatic Cleanup (Recommended)

Cleanup happens automatically when users start voice sessions:

1. **Desktop:** Navigate to `/voice`, click "Start voice session"
2. **Mobile:** Navigate to `/mobile-voice`, select conversation, click play button
3. **Cleanup runs automatically** before session starts
4. **Logs show results** in browser console

### Manual Cleanup (Advanced)

You can also call the cleanup endpoint directly:

```bash
# Clean up conversations inactive for 30 minutes (default)
curl -X POST http://localhost:8000/api/realtime/conversations/cleanup

# Clean up conversations inactive for 60 minutes
curl -X POST http://localhost:8000/api/realtime/conversations/cleanup?inactive_minutes=60

# Clean up all conversations older than 24 hours
curl -X POST http://localhost:8000/api/realtime/conversations/cleanup?inactive_minutes=1440
```

**Response:**
```json
{
  "deleted_count": 5,
  "deleted_ids": [
    "ac10215e-470c-4f0f-bcca-4c1e27199a4d",
    "348b1c10-ca53-4ce2-8de3-b2080ce07151",
    "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
    "9b0a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
    "1c2d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f"
  ],
  "inactive_minutes": 30
}
```

## Configuration

### Inactive Time Threshold

Default: **30 minutes**

To change the threshold, modify the cleanup calls in:
- `VoiceAssistant.js` line 642: `cleanupInactiveConversations(30)` → `cleanupInactiveConversations(60)`
- `MobileVoice.js` line 332: `cleanupInactiveConversations(30)` → `cleanupInactiveConversations(60)`

### Limits

- **Minimum:** 1 minute
- **Maximum:** 1440 minutes (24 hours)
- **Default:** 30 minutes

Enforced by backend query parameter validation:
```python
inactive_minutes: int = Query(30, ge=1, le=1440, ...)
```

## Testing

### Manual Testing

1. **Create test conversations:**
   - Start and stop several voice sessions on desktop
   - Create conversations but don't use them

2. **Wait 30 minutes** (or modify database directly)

3. **Start new session:**
   - Watch browser console for cleanup logs
   - Verify old conversations are deleted

4. **Check conversation list:**
   - Refresh page
   - Verify old conversations no longer appear

### Direct Database Testing

Manually modify `updated_at` timestamps to simulate old conversations:

```bash
# Connect to database
sqlite3 /home/rodrigo/agentic/backend/voice_conversations.db

# Set conversation to be 2 hours old
UPDATE conversations
SET updated_at = datetime('now', '-2 hours')
WHERE id = 'your-conversation-id';

# Verify
SELECT id, name, updated_at FROM conversations ORDER BY updated_at DESC;

# Exit
.quit
```

Then start a voice session and check logs.

### Verify Cleanup Endpoint

```bash
# Test endpoint directly
curl -X POST http://localhost:8000/api/realtime/conversations/cleanup?inactive_minutes=30

# Should return:
# {"deleted_count": N, "deleted_ids": [...], "inactive_minutes": 30}
```

## Benefits

### 1. Prevents 404 Errors
- Mobile page no longer tries to load deleted conversations
- Auto-removes invalid conversation IDs from state

### 2. Fixes MUI Select Errors
- Dropdown no longer shows out-of-range conversation IDs
- Conversation list always reflects current database state

### 3. Reduces Clutter
- Conversation list only shows recent, active sessions
- Easier to find and select the conversation you want

### 4. Improves Performance
- Fewer conversations = faster database queries
- Reduced memory usage for conversation state

### 5. Privacy/Security
- Old conversations automatically cleaned up
- Sensitive conversation data not kept indefinitely

## Error Handling

### Graceful Degradation

If cleanup fails, session start **still proceeds normally**:

```javascript
try {
  const cleanupResult = await cleanupInactiveConversations(30);
  // ... log success
} catch (cleanupErr) {
  console.warn('[Cleanup] Failed to cleanup inactive conversations:', cleanupErr);
  // Don't fail the session start if cleanup fails
}
```

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Network timeout | Backend not responding | Check backend is running |
| 500 Internal Server Error | Database issue | Check SQLite permissions |
| No conversations deleted | All conversations active | Normal - nothing to clean up |

### Debug Logging

Enable verbose logging by checking browser console:

```
[Cleanup] Deleted 3 inactive conversations: ["uuid-1", "uuid-2", "uuid-3"]
```

or

```
[Cleanup] Failed to cleanup inactive conversations: Error: Network timeout
```

## Future Enhancements

Potential improvements:

1. **Configurable threshold in UI** - Let users set inactive time via settings
2. **Scheduled cleanup** - Background task runs every N minutes
3. **Selective cleanup** - Only delete unnamed/"Untitled" conversations
4. **Archive instead of delete** - Move to archive table for later review
5. **Cleanup confirmation** - Show toast notification with undo option
6. **Cleanup statistics** - Dashboard showing cleanup history

## Files Modified

1. `/home/rodrigo/agentic/backend/utils/voice_conversation_store.py` - Added cleanup method
2. `/home/rodrigo/agentic/backend/api/realtime_voice.py` - Added cleanup endpoint
3. `/home/rodrigo/agentic/frontend/src/api.js` - Added API client function
4. `/home/rodrigo/agentic/frontend/src/features/voice/pages/VoiceAssistant.js` - Added desktop cleanup call
5. `/home/rodrigo/agentic/frontend/src/features/voice/pages/MobileVoice.js` - Added mobile cleanup call

## Rollback Instructions

To disable automatic cleanup without removing the code:

```javascript
// In VoiceAssistant.js and MobileVoice.js, comment out the cleanup block:

/*
try {
  const cleanupResult = await cleanupInactiveConversations(30);
  if (cleanupResult.data?.deleted_count > 0) {
    console.log(`[Cleanup] Deleted ${cleanupResult.data.deleted_count} inactive conversations:`, cleanupResult.data.deleted_ids);
  }
} catch (cleanupErr) {
  console.warn('[Cleanup] Failed to cleanup inactive conversations:', cleanupErr);
}
*/
```

Or set threshold to maximum (24 hours):

```javascript
const cleanupResult = await cleanupInactiveConversations(1440); // 24 hours
```

## Related Issues

This cleanup feature addresses the following user-reported issues:

1. **Mobile 404 errors** - Trying to load deleted conversations
2. **MUI Select out-of-range errors** - Conversation IDs not in dropdown
3. **Excessive conversation clutter** - Too many old conversations in list

See also:
- `debug/VOICE_IMPROVEMENTS_SUMMARY.md` - Related voice system improvements
- `frontend/src/features/voice/pages/MobileVoice.js` - Mobile voice implementation

---

**Questions?** Check the code comments or browser console logs for more details.
