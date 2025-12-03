import { useRef, useCallback } from 'react';
import { getWsUrl } from '../../../utils/urlBuilder';

const safeStringify = (value) => {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
};

const truncateText = (value, max = 160) => {
  if (value == null) return '';
  const str = typeof value === 'string' ? value.trim() : String(value);
  if (str.length <= max) return str;
  return `${str.slice(0, max - 1)}…`;
};

/**
 * Team WebSocket management (formerly "nested team")
 */
export const useTeamWebSocket = ({ recordEvent, forwardToVoice, notifyVoiceOfError, setError, dataChannelRef, runCompletedRef, hasSpokenMidRef }) => {
  const teamWsRef = useRef(null);

  /**
   * Setup team WebSocket event handlers
   */
  const setupTeamWebSocketHandlers = useCallback((ws) => {
    ws.onopen = () => {
      void recordEvent('nested', 'system', { message: 'Nested connection established. Awaiting task or user_message.' });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        void recordEvent('nested', msg.type || 'event', msg);
        const type = (msg.type || '').toLowerCase();

        if (type === 'error') {
          const raw = msg.data;
          const detail = typeof raw === 'string'
            ? raw
            : raw?.message || raw?.detail || raw?.error || safeStringify(raw || {});
          notifyVoiceOfError(detail, { source: raw?.source || 'nested_team' });
          setError((prev) => prev || `Nested error: ${typeof detail === 'string' ? detail : safeStringify(detail)}`);
          runCompletedRef.current = true;
          hasSpokenMidRef.current = false;
          return;
        }

        if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
          const content = msg.data.content;
          const source = msg.data.source || 'Agent';
          const text = `[TEAM ${source}] ${content}`;
          forwardToVoice('system', text, { source, kind: 'team_text' });

          // Detect termination marker
          try {
            const cstr = String(content || '');
            if (!runCompletedRef.current && /\bTERMINATE\b/i.test(cstr)) {
              forwardToVoice('system', '[RUN_FINISHED] Team signaled termination. Please provide a concise final summary.', { trigger: 'team_terminate' });
              dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
              runCompletedRef.current = true;
              hasSpokenMidRef.current = false;
            }
          } catch {}
          return;
        }

        if (type === 'toolcallrequestevent' && msg.data && dataChannelRef.current) {
          const toolName = msg.data.name || 'unknown_tool';
          const source = msg.data.source || 'Agent';
          const text = `[TEAM ${source}] Using tool: ${toolName}`;
          forwardToVoice('system', text, { source, kind: 'team_tool_start' });
          return;
        }

        if (type === 'toolcallexecutionevent' && msg.data) {
          const source = msg.data.source || 'Agent';
          const toolName = msg.data.name || (Array.isArray(msg.data.content) && msg.data.content[0]?.name) || 'tool';
          const contentItems = Array.isArray(msg.data.content) ? msg.data.content : [];
          const hasError = msg.data.is_error === true
            || msg.data.status === 'error'
            || msg.data?.result?.is_error === true
            || contentItems.some((item) => item?.is_error || item?.status === 'error');

          if (hasError) {
            const errorDetail = msg.data.error
              || msg.data.result?.error
              || contentItems.find((item) => item?.error)?.error
              || contentItems.find((item) => item?.content)?.content
              || 'Tool execution failed.';
            const detailStr = typeof errorDetail === 'string' ? errorDetail : safeStringify(errorDetail);
            notifyVoiceOfError(`${toolName} reported an error: ${truncateText(detailStr, 220)}`, {
              source,
              tool: toolName,
              kind: 'team_tool_error',
            });
            setError((prev) => prev || `Tool error from ${toolName}: ${detailStr}`);
            runCompletedRef.current = true;
            hasSpokenMidRef.current = false;
          } else if (dataChannelRef.current) {
            const result = msg.data.result || 'completed';
            const text = `[TEAM ${source}] Tool completed: ${typeof result === 'string' ? result.slice(0, 200) : 'success'}`;
            forwardToVoice('system', text, { source, kind: 'team_tool_done' });
          }
          return;
        }

        if (type === 'system' && msg.data && typeof msg.data.message === 'string') {
          const sysMessage = msg.data.message;
          if (/error|failed|exception/i.test(sysMessage)) {
            notifyVoiceOfError(sysMessage, { source: msg.data.source || 'Manager' });
            setError((prev) => prev || `Nested system error: ${sysMessage}`);
            runCompletedRef.current = true;
            hasSpokenMidRef.current = false;
          }
          if (sysMessage.includes('Agent run finished')) {
            if (!runCompletedRef.current && dataChannelRef.current) {
              forwardToVoice('system', '[RUN_FINISHED] Team has completed the task. Please provide a summary.', { trigger: 'team_finished' });
              dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
              hasSpokenMidRef.current = false;
              runCompletedRef.current = true;
            }
            return;
          }
        }

        if (type === 'system' && msg.data && typeof msg.data.message === 'string' && /run (interrupted|cancelled|canceled)/i.test(msg.data.message)) {
          if (dataChannelRef.current && !runCompletedRef.current) {
            forwardToVoice('system', '[RUN_FINISHED] Team run was interrupted. Provide a brief status of what was achieved so far.', { trigger: 'team_interrupted' });
            dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
            hasSpokenMidRef.current = false;
            runCompletedRef.current = true;
          }
          return;
        }
      } catch (e) {
        void recordEvent('nested', 'parse_error', { raw: event.data });
      }
    };

    ws.onerror = (errEvent) => {
      const errorInfo = errEvent?.message || errEvent?.type || 'WebSocket error';
      void recordEvent('nested', 'error', { message: errorInfo });
      notifyVoiceOfError('Nested team connection encountered an error and cannot continue until it is reconnected.', { source: 'controller', kind: 'connection_error' });
      setError((prev) => prev || 'Nested WebSocket encountered an error.');
      runCompletedRef.current = true;
      hasSpokenMidRef.current = false;
    };

    ws.onclose = (closeEvent) => {
      void recordEvent('nested', 'system', { message: 'WebSocket closed', code: closeEvent?.code, reason: closeEvent?.reason });
      if (closeEvent && closeEvent.code !== 1000) {
        const reason = closeEvent.reason || 'Unexpected disconnection.';
        notifyVoiceOfError(`Nested connection closed unexpectedly (${closeEvent.code}). ${reason}`, { source: 'controller', kind: 'connection_error', code: closeEvent.code });
        setError((prev) => prev || `Nested WebSocket closed unexpectedly: ${reason}`);
        runCompletedRef.current = true;
        hasSpokenMidRef.current = false;
      }
      // If the run ended without the explicit finished marker, still prompt a summary
      if (dataChannelRef.current && !runCompletedRef.current) {
        forwardToVoice('system', '[RUN_FINISHED] Team connection closed. Provide the final summary based on received context.', { trigger: 'team_socket_closed' });
        dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
        runCompletedRef.current = true;
        hasSpokenMidRef.current = false;
      }
    };
  }, [recordEvent, notifyVoiceOfError, forwardToVoice, setError, dataChannelRef, runCompletedRef, hasSpokenMidRef]);

  /**
   * Connect to team WebSocket
   */
  const connect = useCallback((agentName) => {
    const teamUrl = getWsUrl(`/runs/${agentName}`);
    const ws = new WebSocket(teamUrl);
    teamWsRef.current = ws;
    setupTeamWebSocketHandlers(ws);
    return ws;
  }, [setupTeamWebSocketHandlers]);

  /**
   * Disconnect team WebSocket
   */
  const disconnect = useCallback(() => {
    if (teamWsRef.current) {
      try {
        teamWsRef.current.close();
      } catch {}
      teamWsRef.current = null;
    }
  }, []);

  /**
   * Send message to team
   */
  const sendMessage = useCallback((text) => {
    if (teamWsRef.current && teamWsRef.current.readyState === WebSocket.OPEN && text.trim()) {
      try {
        teamWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
        void recordEvent('controller', 'system', { message: `Queued user_message to team: ${text}` });
        return true;
      } catch (e) {
        void recordEvent('controller', 'error', { message: `Failed to send to team: ${e.message}` });
        notifyVoiceOfError(`Unable to deliver message to team: ${e.message || e}`, { source: 'controller', kind: 'controller_error' });
        setError((prev) => prev || `Failed to send message to team: ${e.message || e}`);
        return false;
      }
    }
    return false;
  }, [recordEvent, notifyVoiceOfError, setError]);

  return {
    connect,
    disconnect,
    sendMessage,
    setupTeamWebSocketHandlers,
    teamWsRef,
  };
};

export default useTeamWebSocket;
