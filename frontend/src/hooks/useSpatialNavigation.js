import { useEffect, useCallback, useRef } from 'react';

/**
 * Spatial Navigation Hook
 *
 * Enables TV-remote-style arrow key navigation across all focusable elements.
 * Automatically calculates the closest element in the direction of arrow key press.
 *
 * Usage:
 *   const { enabled, setEnabled } = useSpatialNavigation({
 *     enabled: true,
 *     selector: 'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])'
 *   });
 */
export default function useSpatialNavigation({
  enabled = true,
  selector = 'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  excludeSelector = '.spatial-nav-exclude',
  loop = false, // Whether to loop from end to beginning
} = {}) {
  const isEnabledRef = useRef(enabled);

  useEffect(() => {
    isEnabledRef.current = enabled;
  }, [enabled]);

  /**
   * Get all focusable elements on the page
   */
  const getFocusableElements = useCallback(() => {
    const elements = Array.from(document.querySelectorAll(selector));
    return elements.filter(el => {
      // Exclude hidden elements
      if (el.offsetParent === null) return false;

      // Exclude elements with excludeSelector class
      if (excludeSelector && el.matches(excludeSelector)) return false;

      // Exclude elements inside hidden containers
      if (el.closest('[aria-hidden="true"]')) return false;

      return true;
    });
  }, [selector, excludeSelector]);

  /**
   * Get element's center position
   */
  const getElementCenter = useCallback((element) => {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
      rect,
    };
  }, []);

  /**
   * Calculate distance between two points
   */
  const getDistance = useCallback((x1, y1, x2, y2) => {
    return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
  }, []);

  /**
   * Find the best candidate in a given direction
   */
  const findBestCandidate = useCallback((currentElement, direction, elements) => {
    const current = getElementCenter(currentElement);

    const candidates = elements.filter(el => {
      if (el === currentElement) return false;

      const candidate = getElementCenter(el);

      // Filter by direction
      switch (direction) {
        case 'up':
          return candidate.y < current.y;
        case 'down':
          return candidate.y > current.y;
        case 'left':
          return candidate.x < current.x;
        case 'right':
          return candidate.x > current.x;
        default:
          return false;
      }
    });

    if (candidates.length === 0) return null;

    // Find the closest element in the direction
    let best = null;
    let bestScore = Infinity;

    candidates.forEach(el => {
      const candidate = getElementCenter(el);

      let primaryDist, secondaryDist;

      switch (direction) {
        case 'up':
        case 'down':
          primaryDist = Math.abs(candidate.y - current.y);
          secondaryDist = Math.abs(candidate.x - current.x);
          break;
        case 'left':
        case 'right':
          primaryDist = Math.abs(candidate.x - current.x);
          secondaryDist = Math.abs(candidate.y - current.y);
          break;
        default:
          return;
      }

      // Score calculation: prioritize primary direction, then secondary (perpendicular) distance
      // Lower score is better
      const score = primaryDist + (secondaryDist * 0.3);

      if (score < bestScore) {
        bestScore = score;
        best = el;
      }
    });

    return best;
  }, [getElementCenter]);

  /**
   * Handle arrow key navigation
   */
  const handleKeyDown = useCallback((event) => {
    if (!isEnabledRef.current) return;

    const { key } = event;

    // Only handle arrow keys
    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
      return;
    }

    const currentElement = document.activeElement;

    // Skip spatial navigation when inside text input fields
    // to allow normal text cursor movement with arrow keys
    const isTextInput = currentElement && (
      currentElement.tagName === 'TEXTAREA' ||
      (currentElement.tagName === 'INPUT' &&
        ['text', 'password', 'email', 'search', 'url', 'tel', 'number'].includes(currentElement.type)) ||
      currentElement.isContentEditable
    );

    if (isTextInput) {
      return; // Let the browser handle arrow keys normally for text navigation
    }
    const elements = getFocusableElements();

    // If no element is focused, focus the first one
    if (!currentElement || currentElement === document.body) {
      if (elements.length > 0) {
        event.preventDefault();
        elements[0].focus();
      }
      return;
    }

    // Map arrow keys to directions
    const directionMap = {
      'ArrowUp': 'up',
      'ArrowDown': 'down',
      'ArrowLeft': 'left',
      'ArrowRight': 'right',
    };

    const direction = directionMap[key];
    const nextElement = findBestCandidate(currentElement, direction, elements);

    if (nextElement) {
      event.preventDefault();
      nextElement.focus();

      // Scroll into view if needed
      nextElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest',
      });
    } else if (loop) {
      // If looping is enabled and no candidate found, wrap around
      event.preventDefault();

      const current = getElementCenter(currentElement);
      let wrapElement = null;

      switch (direction) {
        case 'up':
          // Go to bottom-most element
          wrapElement = elements.reduce((lowest, el) => {
            const pos = getElementCenter(el);
            const lowestPos = getElementCenter(lowest);
            return pos.y > lowestPos.y ? el : lowest;
          }, elements[0]);
          break;
        case 'down':
          // Go to top-most element
          wrapElement = elements.reduce((highest, el) => {
            const pos = getElementCenter(el);
            const highestPos = getElementCenter(highest);
            return pos.y < highestPos.y ? el : highest;
          }, elements[0]);
          break;
        case 'left':
          // Go to right-most element
          wrapElement = elements.reduce((rightmost, el) => {
            const pos = getElementCenter(el);
            const rightmostPos = getElementCenter(rightmost);
            return pos.x > rightmostPos.x ? el : rightmost;
          }, elements[0]);
          break;
        case 'right':
          // Go to left-most element
          wrapElement = elements.reduce((leftmost, el) => {
            const pos = getElementCenter(el);
            const leftmostPos = getElementCenter(leftmost);
            return pos.x < leftmostPos.x ? el : leftmost;
          }, elements[0]);
          break;
      }

      if (wrapElement) {
        wrapElement.focus();
        wrapElement.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'nearest',
        });
      }
    }
  }, [getFocusableElements, findBestCandidate, getElementCenter, loop]);

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);

  return {
    enabled: isEnabledRef.current,
  };
}
