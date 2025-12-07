/**
 * Utility helper functions for voice assistant
 */

/**
 * Truncate text to max length
 */
export const truncateText = (value, max = 160) => {
  if (value == null) return '';
  const str = typeof value === 'string' ? value.trim() : String(value);
  if (str.length <= max) return str;
  return `${str.slice(0, max - 1)}…`;
};

/**
 * Safe JSON stringify
 */
export const safeStringify = (value) => {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
};

/**
 * Format timestamp for display
 */
export const formatTimestamp = (value) => {
  if (!value) return '';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    const options = sameDay
      ? { hour: 'numeric', minute: '2-digit', second: '2-digit' }
      : { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' };
    return new Intl.DateTimeFormat(undefined, options).format(date);
  } catch (e) {
    return String(value);
  }
};

/**
 * Get conversation title from conversation object
 */
export const getConversationTitle = (conversation, conversationId) => {
  if (!conversation) {
    return conversationId ? `Conversation ${conversationId}` : 'Voice Assistant Conversation';
  }
  const title = conversation.title
    || conversation.name
    || conversation.display_name
    || conversation?.metadata?.title;
  if (title) return title;
  if (conversationId) return `Conversation ${conversationId}`;
  return 'Voice Assistant Conversation';
};
