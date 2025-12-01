import { useEffect, useCallback, useRef, useState } from 'react';

/**
 * Global keyboard shortcuts configuration
 */
export const KEYBOARD_SHORTCUTS = {
  // Navigation
  AGENTS: { key: '1', alt: true, description: 'Go to Agents page' },
  TOOLS: { key: '2', alt: true, description: 'Go to Tools page' },
  VOICE: { key: '3', alt: true, description: 'Go to Voice page' },
  HELP: { key: '?', ctrl: true, description: 'Show keyboard shortcuts help' },

  // Voice controls
  VOICE_START_STOP: { key: 's', ctrl: true, description: 'Start/Stop voice session' },
  VOICE_MUTE: { key: 'm', ctrl: true, description: 'Toggle microphone mute' },
  VOICE_SPEAKER: { key: 'k', ctrl: true, description: 'Toggle speaker mute' },

  // Agent controls
  AGENT_RUN: { key: 'r', ctrl: true, description: 'Run agent' },
  AGENT_STOP: { key: 'x', ctrl: true, description: 'Stop agent' },
  AGENT_CLEAR: { key: 'l', ctrl: true, shift: true, description: 'Clear console' },

  // General
  SEARCH: { key: 'f', ctrl: true, description: 'Focus search/input field' },
  SAVE: { key: 's', ctrl: true, shift: true, description: 'Save current form' },
  ESCAPE: { key: 'Escape', description: 'Close dialogs/reset focus' },
};

/**
 * Custom hook for keyboard navigation
 * @param {Object} options - Configuration options
 * @param {Object} options.shortcuts - Custom keyboard shortcuts handlers
 * @param {boolean} options.enabled - Enable/disable keyboard navigation
 * @param {Function} options.onHelp - Callback when help is requested
 *
 * Note: This hook does NOT include page navigation (Alt+1/2/3) to avoid Router context issues.
 * Page navigation is handled by KeyboardNavigationProvider component.
 */
export default function useKeyboardNavigation({
  shortcuts = {},
  enabled = true,
  onHelp = null
} = {}) {
  const shortcutsRef = useRef(shortcuts);

  // Update shortcuts ref when they change
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event) => {
    if (!enabled) return;

    const { key, altKey, ctrlKey, shiftKey, metaKey } = event;

    // Check for help shortcut
    if (key === '?' && ctrlKey && !shiftKey && !altKey && !metaKey) {
      event.preventDefault();
      if (onHelp) onHelp();
      return;
    }

    // Check for custom shortcuts
    const customShortcuts = shortcutsRef.current;
    Object.entries(customShortcuts).forEach(([name, handler]) => {
      const shortcut = KEYBOARD_SHORTCUTS[name];
      if (!shortcut) return;

      const keyMatch = shortcut.key.toLowerCase() === key.toLowerCase();
      const altMatch = !!shortcut.alt === altKey;
      const ctrlMatch = !!shortcut.ctrl === ctrlKey;
      const shiftMatch = !!shortcut.shift === shiftKey;
      const metaMatch = !!shortcut.meta === metaKey;

      if (keyMatch && altMatch && ctrlMatch && shiftMatch && metaMatch) {
        event.preventDefault();
        if (typeof handler === 'function') {
          handler(event);
        }
      }
    });
  }, [enabled, onHelp]);

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);

  return {
    shortcuts: KEYBOARD_SHORTCUTS,
  };
}

/**
 * Custom hook for focus management
 * @param {Object} options - Configuration options
 */
export function useFocusManagement({
  autoFocus = false,
  trapFocus = false,
  returnFocus = true
} = {}) {
  const containerRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      previouslyFocusedRef.current = document.activeElement;

      // Focus first focusable element
      const focusableElements = containerRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    }

    return () => {
      if (returnFocus && previouslyFocusedRef.current) {
        previouslyFocusedRef.current.focus();
      }
    };
  }, [autoFocus, returnFocus]);

  useEffect(() => {
    if (!trapFocus || !containerRef.current) return;

    const handleKeyDown = (event) => {
      if (event.key !== 'Tab') return;

      const focusableElements = containerRef.current.querySelectorAll(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [trapFocus]);

  return {
    containerRef,
  };
}

/**
 * Custom hook for list navigation (up/down arrow keys)
 * @param {Array} items - List items
 * @param {Function} onSelect - Callback when item is selected
 */
export function useListNavigation(items = [], onSelect = null) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef(null);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (!items.length) return;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, items.length - 1));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          event.preventDefault();
          if (onSelect && items[selectedIndex]) {
            onSelect(items[selectedIndex], selectedIndex);
          }
          break;
        default:
          break;
      }
    };

    const container = listRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => {
        container.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [items, selectedIndex, onSelect]);

  return {
    listRef,
    selectedIndex,
    setSelectedIndex,
  };
}
