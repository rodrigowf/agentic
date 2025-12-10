import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import useSpatialNavigation from '../hooks/useSpatialNavigation';

/**
 * Detect if running in Android TV WebView
 * Checks user agent for Android TV indicators
 */
const isAndroidTV = () => {
  const ua = navigator.userAgent || '';
  // Android TV WebViews typically have "Android" + one of: "TV", "AFT" (Amazon Fire TV),
  // "BRAVIA", "SHIELD", or lack "Mobile" while having "Android"
  const isAndroid = /Android/i.test(ua);
  const hasTV = /TV|AFT|BRAVIA|SHIELD|GoogleTV|Chromecast/i.test(ua);
  const isMobile = /Mobile/i.test(ua);

  // Android device with TV indicator, or Android without Mobile (could be TV/tablet)
  // Also check for leanback (Android TV launcher)
  const hasLeanback = /leanback/i.test(ua);

  return isAndroid && (hasTV || hasLeanback || !isMobile);
};

/**
 * SpatialNavigationContext - Provides spatial navigation state and controls
 */
const SpatialNavigationContext = createContext({
  enabled: false,
  toggleEnabled: () => {},
  isTV: false,
});

/**
 * SpatialNavigationProvider - Enables TV-remote-style arrow key navigation
 *
 * Wraps the app and provides spatial navigation throughout.
 * Only enabled on Android TV WebView - disabled on desktop/mobile browsers.
 *
 * Features:
 * - Arrow keys navigate in 2D space
 * - Automatically finds closest element in direction
 * - Smooth scrolling to focused elements
 * - Can be toggled on/off via context
 * - Auto-detects Android TV environment
 *
 * Usage:
 *   <SpatialNavigationProvider>
 *     <App />
 *   </SpatialNavigationProvider>
 */
export function SpatialNavigationProvider({ children }) {
  // Detect TV environment once on mount
  const isTV = useMemo(() => isAndroidTV(), []);

  // Load initial state from localStorage, but default to TV detection result
  const [enabled, setEnabled] = useState(() => {
    const stored = localStorage.getItem('spatialNavigationEnabled');
    // If explicitly set in localStorage, use that; otherwise use TV detection
    return stored !== null ? stored === 'true' : isTV;
  });

  // Toggle spatial navigation on/off
  const toggleEnabled = useCallback(() => {
    setEnabled(prev => {
      const newValue = !prev;
      localStorage.setItem('spatialNavigationEnabled', String(newValue));
      return newValue;
    });
  }, []);

  // Enable the spatial navigation hook
  useSpatialNavigation({
    enabled,
    loop: false, // Set to true if you want wrap-around navigation
  });

  const value = {
    enabled,
    toggleEnabled,
    isTV,
  };

  return (
    <SpatialNavigationContext.Provider value={value}>
      {children}
    </SpatialNavigationContext.Provider>
  );
}

/**
 * Hook to access spatial navigation context
 */
export function useSpatialNavigationContext() {
  const context = useContext(SpatialNavigationContext);
  if (!context) {
    throw new Error('useSpatialNavigationContext must be used within SpatialNavigationProvider');
  }
  return context;
}

export default SpatialNavigationProvider;
