/**
 * Tool execution logic for voice model tools
 */

const TOOL_AUTOPAUSE_WINDOW_MS = 1200;

export const createToolExecutor = ({
  teamWsRef,
  claudeCodeWsRef,
  voiceConfig,
  recordEvent,
  notifyVoiceOfError,
  setError,
  lastVoiceToolCallRef,
  hasSpokenMidRef,
  runCompletedRef,
  setupTeamWebSocketHandlers,
  setSharedTeamWs,
  getWsUrl,
}) => {
  /**
   * Execute a tool call from the voice model
   */
  const executeToolCall = async (callId, name, argsObj) => {
    try {
      if (name === 'send_to_nested') {
        const text = (argsObj && typeof argsObj.text === 'string') ? argsObj.text : '';
        if (!text) throw new Error('Missing text');
        if (teamWsRef.current && teamWsRef.current.readyState === WebSocket.OPEN) {
          hasSpokenMidRef.current = false; // new task; allow one mid-run narration
          runCompletedRef.current = false; // new task; clear completion flag
          teamWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
          void recordEvent('controller', 'tool_exec', { tool: name, args: argsObj });
          lastVoiceToolCallRef.current = { name, timestamp: Date.now() };
          return { ok: true };
        }
        throw new Error('Team WebSocket not connected');
      }

      if (name === 'send_to_claude_code') {
        const text = (argsObj && typeof argsObj.text === 'string') ? argsObj.text : '';
        if (!text) throw new Error('Missing text');
        if (claudeCodeWsRef.current && claudeCodeWsRef.current.readyState === WebSocket.OPEN) {
          claudeCodeWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
          void recordEvent('controller', 'tool_exec', { tool: name, args: argsObj });
          lastVoiceToolCallRef.current = { name, timestamp: Date.now() };
          return { ok: true };
        }
        throw new Error('Claude Code WebSocket not connected');
      }

      if (name === 'pause') {
        const now = Date.now();
        const lastCall = lastVoiceToolCallRef.current;
        if (lastCall?.name === 'send_to_nested' && now - lastCall.timestamp <= TOOL_AUTOPAUSE_WINDOW_MS) {
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'Ignored automatic pause immediately after send_to_nested.' });
          lastVoiceToolCallRef.current = { name: 'pause_ignored', timestamp: now };
          return { ok: true };
        }
        if (teamWsRef.current && teamWsRef.current.readyState === WebSocket.OPEN) {
          teamWsRef.current.send(JSON.stringify({ type: 'cancel' }));
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'Pause command sent to team' });
        } else {
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'No active team connection to pause' });
        }
        lastVoiceToolCallRef.current = { name, timestamp: now };
        return { ok: true };
      }

      if (name === 'reset') {
        const now = Date.now();
        const lastCall = lastVoiceToolCallRef.current;
        if (lastCall?.name === 'send_to_nested' && now - lastCall.timestamp <= TOOL_AUTOPAUSE_WINDOW_MS) {
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'Ignored automatic reset immediately after send_to_nested.' });
          lastVoiceToolCallRef.current = { name: 'reset_ignored', timestamp: now };
          return { ok: true };
        }
        // Best effort: close and reopen WS without auto-running
        try { if (teamWsRef.current) teamWsRef.current.close(); } catch {}
        const agentName = voiceConfig.agentName || 'MainConversation';
        const teamUrl = getWsUrl(`/runs/${agentName}`);
        const ws = new WebSocket(teamUrl);
        teamWsRef.current = ws;
        setSharedTeamWs(ws);
        hasSpokenMidRef.current = false;
        runCompletedRef.current = false;
        setupTeamWebSocketHandlers(ws);
        void recordEvent('controller', 'tool_exec', { tool: name });
        lastVoiceToolCallRef.current = { name, timestamp: now };
        return { ok: true };
      }

      if (name === 'pause_claude_code') {
        const now = Date.now();
        if (claudeCodeWsRef.current && claudeCodeWsRef.current.readyState === WebSocket.OPEN) {
          claudeCodeWsRef.current.send(JSON.stringify({ type: 'cancel' }));
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'Pause/cancel command sent to Claude Code' });
        } else {
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'No active Claude Code connection to pause' });
        }
        lastVoiceToolCallRef.current = { name, timestamp: now };
        return { ok: true };
      }

      throw new Error(`Unknown tool: ${name}`);
    } catch (e) {
      const message = String(e?.message || e);
      void recordEvent('controller', 'tool_error', { tool: name, error: message });
      notifyVoiceOfError(`Tool ${name} failed: ${message}`, { source: 'controller', tool: name, kind: 'controller_tool_error' });
      setError((prev) => prev || `Tool ${name} failed: ${message}`);
      return { ok: false, error: message };
    }
  };

  return {
    executeToolCall,
  };
};

export default createToolExecutor;
