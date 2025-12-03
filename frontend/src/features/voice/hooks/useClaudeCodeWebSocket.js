import { useRef, useCallback } from 'react';
import { getWsUrl } from '../../../utils/urlBuilder';

/**
 * Claude Code WebSocket management
 */
export const useClaudeCodeWebSocket = ({ recordEvent, forwardToVoice, notifyVoiceOfError, dataChannelRef }) => {
  const claudeCodeWsRef = useRef(null);

  /**
   * Connect to Claude Code WebSocket
   */
  const connect = useCallback(() => {
    const claudeCodeUrl = getWsUrl('/runs/ClaudeCode');
    const claudeCodeWs = new WebSocket(claudeCodeUrl);
    claudeCodeWsRef.current = claudeCodeWs;

    claudeCodeWs.onopen = () => {
      void recordEvent('claude_code', 'system', { message: 'Claude Code connection established.' });
    };

    claudeCodeWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        void recordEvent('claude_code', msg.type || 'event', msg);
        const type = (msg.type || '').toLowerCase();

        if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
          const content = msg.data.content;
          const source = msg.data.source || 'ClaudeCode';
          const text = `[CODE ${source}] ${content}`;
          forwardToVoice('system', text, { source, kind: 'code_text' });
        }

        if (type === 'taskresult' && msg.data) {
          const outcome = msg.data.outcome || 'completed';
          const message = msg.data.message || '';
          if (outcome === 'error') {
            notifyVoiceOfError(`Claude Code error: ${message}`, { source: 'claude_code' });
          } else if (dataChannelRef.current) {
            const text = `[CODE RESULT] ${message || 'Task completed'}`;
            forwardToVoice('system', text, { source: 'claude_code', kind: 'code_result' });
          }
        }
      } catch (e) {
        void recordEvent('claude_code', 'parse_error', { raw: event.data });
      }
    };

    claudeCodeWs.onerror = (errEvent) => {
      const errorInfo = errEvent?.message || errEvent?.type || 'WebSocket error';
      void recordEvent('claude_code', 'error', { message: errorInfo });
      notifyVoiceOfError('Claude Code connection encountered an error.', { source: 'controller', kind: 'connection_error' });
    };

    claudeCodeWs.onclose = (closeEvent) => {
      void recordEvent('claude_code', 'system', { message: 'Claude Code WebSocket closed', code: closeEvent?.code, reason: closeEvent?.reason });
    };

    return claudeCodeWs;
  }, [recordEvent, forwardToVoice, notifyVoiceOfError, dataChannelRef]);

  /**
   * Disconnect Claude Code WebSocket
   */
  const disconnect = useCallback(() => {
    if (claudeCodeWsRef.current) {
      try {
        claudeCodeWsRef.current.close();
      } catch {}
      claudeCodeWsRef.current = null;
    }
  }, []);

  /**
   * Send message to Claude Code
   */
  const sendMessage = useCallback((text) => {
    if (claudeCodeWsRef.current && claudeCodeWsRef.current.readyState === WebSocket.OPEN && text.trim()) {
      try {
        claudeCodeWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
        void recordEvent('controller', 'system', { message: `Queued user_message to claude: ${text}` });
        return true;
      } catch (e) {
        void recordEvent('controller', 'error', { message: `Failed to send to claude: ${e.message}` });
        notifyVoiceOfError(`Unable to deliver message to Claude Code: ${e.message || e}`, { source: 'controller', kind: 'controller_error' });
        return false;
      }
    }
    return false;
  }, [recordEvent, notifyVoiceOfError]);

  return {
    connect,
    disconnect,
    sendMessage,
    claudeCodeWsRef,
  };
};

export default useClaudeCodeWebSocket;
