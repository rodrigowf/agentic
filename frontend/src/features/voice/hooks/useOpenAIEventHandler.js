import { useCallback } from 'react';

/**
 * Handle OpenAI Realtime API events from data channel
 * Processes tool calls, argument deltas, and completions
 */
export const useOpenAIEventHandler = ({ toolCallsRef }) => {
  /**
   * Handle incoming OpenAI event
   * @param {Object} payload - Event payload from data channel
   * @param {Object} context - Context object with executeToolCall function
   */
  const handleEvent = useCallback(async (payload, { executeToolCall }) => {
    const t = payload?.type;

    // New schema: function call item added to response output
    if (t === 'response.output_item.added' && payload?.item?.type === 'function_call') {
      const callItem = payload.item;
      const name = callItem?.name;
      const callId = callItem?.call_id;
      if (name && callId) toolCallsRef.current[callId] = { name, args: '' };
      return;
    }

    // New schema: argument deltas come via response.function_call_arguments.delta
    if (t === 'response.function_call_arguments.delta') {
      const id = payload?.call_id || payload?.function_call_id || payload?.id;
      const delta = payload?.delta || payload?.arguments || '';
      if (id && toolCallsRef.current[id]) toolCallsRef.current[id].args += String(delta);
      return;
    }

    // New schema: arguments done (finalize and execute)
    if (t === 'response.function_call_arguments.done') {
      const id = payload?.call_id || payload?.function_call_id || payload?.id;
      const entry = id ? toolCallsRef.current[id] : undefined;
      if (entry) {
        let argsObj = {};
        try {
          argsObj = entry.args ? JSON.parse(entry.args) : {};
        } catch {}
        await executeToolCall(id, entry.name, argsObj);
        delete toolCallsRef.current[id];
      }
      return;
    }

    // Legacy schema support (older events)
    if (t === 'response.function_call') {
      const id = payload?.id || payload?.function_call_id || payload?.call_id;
      const name = payload?.name;
      if (id && name) toolCallsRef.current[id] = { name, args: '' };
      return;
    }

    if (t === 'response.function_call.arguments.delta') {
      const id = payload?.id || payload?.function_call_id || payload?.call_id;
      const delta = payload?.delta || payload?.arguments || '';
      if (id && toolCallsRef.current[id]) toolCallsRef.current[id].args += String(delta);
      return;
    }

    if (t === 'response.function_call.completed') {
      const id = payload?.id || payload?.function_call_id || payload?.call_id;
      const entry = id ? toolCallsRef.current[id] : undefined;
      if (entry) {
        let argsObj = {};
        try {
          argsObj = entry.args ? JSON.parse(entry.args) : {};
        } catch {}
        await executeToolCall(id, entry.name, argsObj);
        delete toolCallsRef.current[id];
      }
      return;
    }
  }, [toolCallsRef]);

  return {
    handleEvent,
  };
};

export default useOpenAIEventHandler;
