import { useEffect, useRef, useCallback } from 'react';

/**
 * useTVNavigation - Custom hook for TV remote control navigation
 *
 * Enables arrow key navigation between focusable elements on TV interfaces.
 * Automatically finds the nearest element in the direction of arrow press.
 *
 * IMPORTANT: Only activates when:
 * 1. A focusable element with data-tv-focusable is focused (not regular inputs/textareas)
 * 2. Or when explicitly enabled via props
 *
 * This ensures normal PC keyboard navigation is NOT affected!
 *
 * @param {Object} options - Configuration options
 * @param {boolean} options.enabled - Whether navigation is always enabled (default: false for PC compatibility)
 * @param {string} options.selector - CSS selector for focusable elements (default: '[data-tv-focusable]')
 * @param {Function} options.onEnter - Callback when Enter/OK is pressed on focused element
 */
export default function useTVNavigation({
  enabled = false,
  selector = '[data-tv-focusable="true"]',
  onEnter = null,
} = {}) {
  const containerRef = useRef(null);
  const currentFocusIndexRef = useRef(0);

  /**
   * Get all focusable elements within the container
   */
  const getFocusableElements = useCallback(() => {
    if (!containerRef.current) return [];
    const elements = Array.from(containerRef.current.querySelectorAll(selector));
    // Filter out disabled elements
    return elements.filter(el => !el.disabled && !el.hasAttribute('disabled'));
  }, [selector]);

  /**
   * Calculate the center point of an element
   */
  const getElementCenter = (element) => {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
      rect,
    };
  };

  /**
   * Calculate distance between two points
   */
  const getDistance = (p1, p2) => {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
  };

  /**
   * Find the nearest element in a given direction
   */
  const findNearestInDirection = useCallback((currentElement, direction, elements) => {
    const currentCenter = getElementCenter(currentElement);
    let candidates = [];

    elements.forEach((element) => {
      if (element === currentElement) return;

      const targetCenter = getElementCenter(element);
      const dx = targetCenter.x - currentCenter.x;
      const dy = targetCenter.y - currentCenter.y;

      // Check if element is in the right direction
      let isInDirection = false;
      let primaryDistance = 0;
      let secondaryDistance = 0;

      switch (direction) {
        case 'up':
          isInDirection = dy < -5; // Some threshold to avoid same-row elements
          primaryDistance = Math.abs(dy);
          secondaryDistance = Math.abs(dx);
          break;
        case 'down':
          isInDirection = dy > 5;
          primaryDistance = Math.abs(dy);
          secondaryDistance = Math.abs(dx);
          break;
        case 'left':
          isInDirection = dx < -5;
          primaryDistance = Math.abs(dx);
          secondaryDistance = Math.abs(dy);
          break;
        case 'right':
          isInDirection = dx > 5;
          primaryDistance = Math.abs(dx);
          secondaryDistance = Math.abs(dy);
          break;
        default:
          break;
      }

      if (isInDirection) {
        candidates.push({
          element,
          distance: getDistance(currentCenter, targetCenter),
          primaryDistance,
          secondaryDistance,
        });
      }
    });

    if (candidates.length === 0) return null;

    // Sort by primary distance first, then secondary distance
    candidates.sort((a, b) => {
      const primaryDiff = a.primaryDistance - b.primaryDistance;
      if (Math.abs(primaryDiff) > 10) return primaryDiff;
      return a.secondaryDistance - b.secondaryDistance;
    });

    return candidates[0].element;
  }, []);

  /**
   * Focus an element and scroll it into view
   */
  const focusElement = useCallback((element) => {
    if (!element) return;

    element.focus();

    // Scroll into view with smooth behavior
    setTimeout(() => {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'center',
      });
    }, 0);

    // Add visual focus indicator
    element.setAttribute('data-tv-focused', 'true');
  }, []);

  /**
   * Remove focus indicator from all elements
   */
  const clearFocusIndicators = useCallback(() => {
    const elements = getFocusableElements();
    elements.forEach(el => el.removeAttribute('data-tv-focused'));
  }, [getFocusableElements]);

  /**
   * Handle arrow key navigation
   */
  const handleKeyDown = useCallback((event) => {
    const key = event.key;
    const isArrowKey = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key);
    const isEnterKey = key === 'Enter';

    if (!isArrowKey && !isEnterKey) return;

    // IMPORTANT: Only intercept if we're in TV navigation mode
    // This preserves normal PC keyboard navigation!
    const activeElement = document.activeElement;
    const isTVFocusable = activeElement?.hasAttribute('data-tv-focusable');
    const isInTVMode = enabled || isTVFocusable;

    // Don't interfere with normal text inputs, textareas, or contenteditable
    const isTextInput = activeElement?.tagName === 'INPUT' &&
                        (activeElement?.type === 'text' || activeElement?.type === 'search');
    const isTextArea = activeElement?.tagName === 'TEXTAREA';
    const isContentEditable = activeElement?.contentEditable === 'true';

    // Only proceed if in TV mode AND not in a text input
    if (!isInTVMode || (isArrowKey && (isTextInput || isTextArea || isContentEditable))) {
      return;
    }

    const elements = getFocusableElements();
    if (elements.length === 0) return;

    // Get currently focused element
    const currentElement = elements.includes(activeElement) ? activeElement : elements[0];

    if (isEnterKey) {
      // Trigger click or custom callback
      event.preventDefault();
      if (onEnter) {
        onEnter(currentElement);
      } else {
        currentElement.click();
      }
      return;
    }

    // Handle arrow navigation
    event.preventDefault();

    const directionMap = {
      'ArrowUp': 'up',
      'ArrowDown': 'down',
      'ArrowLeft': 'left',
      'ArrowRight': 'right',
    };

    const direction = directionMap[key];
    const nextElement = findNearestInDirection(currentElement, direction, elements);

    if (nextElement) {
      clearFocusIndicators();
      focusElement(nextElement);
    }
  }, [enabled, getFocusableElements, findNearestInDirection, focusElement, clearFocusIndicators, onEnter]);

  /**
   * Initialize focus on first element (only when explicitly enabled)
   */
  const initializeFocus = useCallback(() => {
    // Only auto-focus if explicitly enabled (TV mode)
    if (!enabled) return;

    const elements = getFocusableElements();
    if (elements.length > 0 && !elements.includes(document.activeElement)) {
      focusElement(elements[0]);
    }
  }, [enabled, getFocusableElements, focusElement]);

  /**
   * Set up keyboard event listeners
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;

    // Add event listener (always, but it checks internally if should activate)
    container.addEventListener('keydown', handleKeyDown);

    // Only initialize focus if explicitly enabled (TV mode)
    let timer;
    if (enabled) {
      timer = setTimeout(initializeFocus, 100);
    }

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      if (timer) clearTimeout(timer);
    };
  }, [enabled, handleKeyDown, initializeFocus]);

  /**
   * Manually trigger focus on first element
   */
  const focusFirst = useCallback(() => {
    const elements = getFocusableElements();
    if (elements.length > 0) {
      clearFocusIndicators();
      focusElement(elements[0]);
    }
  }, [getFocusableElements, focusElement, clearFocusIndicators]);

  return {
    containerRef,
    focusFirst,
  };
}
