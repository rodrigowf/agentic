/**
 * Voice message forwarding logic
 * Handles forwarding messages from nested team/claude to voice model
 */

const MAX_REPLAY_ITEMS = 50;

export const createVoiceForwarder = ({
  dataChannelRef,
  replayQueueRef,
  recordEvent,
  hasSpokenMidRef,
  runCompletedRef,
}) => {
  /**
   * Forward text message to voice model
   * @param {string} role - Message role (user, system, assistant)
   * @param {string} rawText - Text to forward
   * @param {Object} metadata - Optional metadata (kind, trigger, forceResponse, speak)
   */
  const forwardToVoice = (role, rawText, metadata = {}) => {
    const text = (rawText ?? '').toString().trim();
    if (!text) return;

    const kind = metadata?.kind;
    const trigger = metadata?.trigger;
    const forceResponse = metadata?.forceResponse === true;

    const item = {
      type: 'message',
      role: role || 'system',
      content: [{ type: 'input_text', text }],
    };

    // Clone for replay queue
    let cloneForQueue = item;
    try {
      cloneForQueue = JSON.parse(JSON.stringify(item));
    } catch {
      cloneForQueue = { ...item };
    }
    replayQueueRef.current = [...(replayQueueRef.current || []), cloneForQueue].slice(-MAX_REPLAY_ITEMS);

    const channel = dataChannelRef.current;
    const diagnostics = { role, text, metadata };

    const errorKinds = new Set(['team_error', 'team_tool_error', 'controller_error', 'controller_tool_error']);
    let shouldRequestResponse = forceResponse || errorKinds.has(kind);
    let markMidSpoken = false;

    if (!shouldRequestResponse && kind === 'team_tool_done' && !runCompletedRef.current && !hasSpokenMidRef.current) {
      shouldRequestResponse = true;
      markMidSpoken = true;
    }

    // Allow explicit opt-in via metadata.speak === true
    if (!shouldRequestResponse && metadata?.speak === true) {
      shouldRequestResponse = true;
    }

    // Final summary triggers are handled elsewhere
    if (trigger) {
      shouldRequestResponse = forceResponse || metadata?.speak === true;
    }

    if (!channel || channel.readyState !== 'open') {
      void recordEvent('controller', 'voice_forward_pending', { ...diagnostics, requested_response: shouldRequestResponse });
      return;
    }

    try {
      channel.send(JSON.stringify({ type: 'conversation.item.create', item }));
      if (shouldRequestResponse) {
        channel.send(JSON.stringify({ type: 'response.create' }));
        if (markMidSpoken) {
          hasSpokenMidRef.current = true;
        }
      }
      void recordEvent('controller', 'voice_forward', { ...diagnostics, item, requested_response: shouldRequestResponse });
    } catch (err) {
      console.error('Failed to forward to voice', err);
      void recordEvent('controller', 'voice_forward_error', {
        ...diagnostics,
        error: err?.message || String(err),
        requested_response: shouldRequestResponse,
      });
    }
  };

  /**
   * Notify voice of error
   */
  const notifyVoiceOfError = (message, metadata = {}) => {
    const detailText = (message ?? '').toString().trim() || 'An unexpected error occurred.';
    const formatted = detailText.startsWith('[TEAM ERROR]') ? detailText : `[TEAM ERROR] ${detailText}`;
    const detailMetadata = { ...metadata };
    if (!detailMetadata.kind) detailMetadata.kind = 'team_error';
    forwardToVoice('system', formatted, detailMetadata);
  };

  return {
    forwardToVoice,
    notifyVoiceOfError,
  };
};

export default createVoiceForwarder;
