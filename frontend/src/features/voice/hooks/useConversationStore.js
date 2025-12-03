import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import {
  getVoiceConversation,
  connectVoiceConversationStream,
  appendVoiceConversationEvent,
} from '../../../api';

const MAX_REPLAY_ITEMS = 50;

/**
 * Manages conversation persistence, event storage, and WebSocket streaming
 */
export const useConversationStore = (conversationId) => {
  const [conversation, setConversation] = useState(null);
  const [conversationLoading, setConversationLoading] = useState(true);
  const [conversationError, setConversationError] = useState(null);
  const [messages, setMessages] = useState([]);

  const eventsMapRef = useRef(new Map());
  const streamRef = useRef(null);
  const replayQueueRef = useRef([]);

  const normalizeEvent = useCallback((event) => {
    if (!event) return null;
    const { id, timestamp, source, type, payload } = event;
    return {
      id,
      timestamp,
      source,
      type,
      data: payload ?? {},
    };
  }, []);

  const upsertEvents = useCallback((incoming) => {
    if (!incoming || incoming.length === 0) return;
    const map = eventsMapRef.current;
    incoming.forEach((item) => {
      if (!item || typeof item.id === 'undefined' || item.id === null) return;
      map.set(item.id, item);
    });
    const sorted = Array.from(map.values()).sort((a, b) => {
      const aId = typeof a.id === 'number' ? a.id : Number(a.id) || 0;
      const bId = typeof b.id === 'number' ? b.id : Number(b.id) || 0;
      return aId - bId;
    });
    setMessages(sorted);
  }, []);

  const recordEvent = useCallback(async (source, type, payload) => {
    if (!conversationId) return null;
    try {
      const res = await appendVoiceConversationEvent(conversationId, {
        source,
        type,
        payload,
      });
      const normalized = normalizeEvent(res.data);
      if (normalized) {
        upsertEvents([normalized]);
        setConversation((prev) => (prev ? { ...prev, updated_at: normalized.timestamp } : prev));
      }
      return normalized;
    } catch (err) {
      console.error('Failed to persist conversation event', err);
      return null;
    }
  }, [conversationId, normalizeEvent, upsertEvents]);

  const buildReplayItems = useCallback(() => {
    if (!messages || messages.length === 0) return [];
    const items = [];
    messages.forEach((msg) => {
      if (!msg || !msg.data) return;
      const sourceLower = (msg.source || '').toLowerCase();
      const typeLower = (msg.type || '').toLowerCase();
      if (sourceLower === 'user' && typeLower === 'voice_user_message') {
        const text = msg.data?.text || msg.data?.transcript || msg.data?.message;
        if (text) {
          items.push({
            type: 'message',
            role: 'user',
            content: [{ type: 'input_text', text }],
          });
        }
      }
      if (sourceLower === 'controller' && (typeLower === 'voice_forward' || typeLower === 'voice_forward_pending')) {
        const text = msg.data?.text || msg.data?.message;
        if (text) {
          const item = {
            type: 'message',
            role: msg.data?.role || 'system',
            content: [{ type: 'input_text', text }],
          };
          if (msg.data?.metadata && Object.keys(msg.data.metadata).length > 0) {
            item.metadata = msg.data.metadata;
          }
          items.push(item);
        }
      }
    });
    return items;
  }, [messages]);

  const remoteSessionActive = useMemo(() => {
    let lastStart = null;
    let lastStop = null;
    messages.forEach((msg) => {
      if ((msg.source || '').toLowerCase() !== 'controller') return;
      if ((msg.type || '').toLowerCase() === 'session_started') {
        lastStart = msg.timestamp;
      }
      if ((msg.type || '').toLowerCase() === 'session_stopped' || (msg.type || '').toLowerCase() === 'session_error') {
        lastStop = msg.timestamp;
      }
    });
    if (!lastStart) return false;
    if (!lastStop) return true;
    return new Date(lastStart).getTime() > new Date(lastStop).getTime();
  }, [messages]);

  // Load conversation on mount
  useEffect(() => {
    if (!conversationId) {
      setConversation(null);
      setConversationLoading(false);
      setConversationError('Missing conversation id in URL');
      return;
    }
    let cancelled = false;
    setConversationLoading(true);
    setConversationError(null);
    (async () => {
      try {
        const res = await getVoiceConversation(conversationId, { limit: 1000 });
        if (cancelled) return;
        const detail = res.data;
        setConversation(detail);
        eventsMapRef.current.clear();
        if (detail?.events?.length) {
          const normalized = detail.events.map((evt) => normalizeEvent(evt)).filter(Boolean);
          upsertEvents(normalized);
        } else {
          setMessages([]);
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load conversation', err);
        setConversation(null);
        setConversationError(err?.response?.data?.detail || err.message || 'Conversation not found');
      } finally {
        if (!cancelled) setConversationLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conversationId, normalizeEvent, upsertEvents]);

  // Setup WebSocket stream for real-time events
  useEffect(() => {
    if (!conversationId) return undefined;
    const socket = connectVoiceConversationStream(conversationId, { limit: 1000 });
    streamRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload?.type === 'history') {
          const normalized = (payload.events || []).map((evt) => normalizeEvent(evt)).filter(Boolean);
          if (normalized.length) upsertEvents(normalized);
          return;
        }
        if (payload?.type === 'event' && payload.event) {
          const normalized = normalizeEvent(payload.event);
          if (normalized) upsertEvents([normalized]);
        }
      } catch (err) {
        console.error('Failed to parse conversation stream message', err);
      }
    };

    socket.onerror = (event) => {
      console.error('Conversation stream error', event);
    };

    socket.onclose = () => {
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };

    return () => {
      try {
        socket.close();
      } catch (e) {
        /* noop */
      }
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };
  }, [conversationId, normalizeEvent, upsertEvents]);

  return {
    // State
    conversation,
    conversationLoading,
    conversationError,
    messages,
    remoteSessionActive,

    // Refs
    replayQueueRef,

    // Methods
    recordEvent,
    buildReplayItems,
    upsertEvents,
  };
};

export default useConversationStore;
