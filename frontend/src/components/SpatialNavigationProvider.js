import React, { createContext, useContext, useState, useCallback } from 'react';
import useSpatialNavigation from '../hooks/useSpatialNavigation';

/**
 * SpatialNavigationContext - Provides spatial navigation state and controls
 */
const SpatialNavigationContext = createContext({
  enabled: true,
  toggleEnabled: () => {},
});

/**
 * SpatialNavigationProvider - Enables TV-remote-style arrow key navigation
 *
 * Wraps the app and provides spatial navigation throughout.
 * Users can navigate all focusable elements using arrow keys.
 *
 * Features:
 * - Arrow keys navigate in 2D space
 * - Automatically finds closest element in direction
 * - Smooth scrolling to focused elements
 * - Can be toggled on/off via context
 *
 * Usage:
 *   <SpatialNavigationProvider>
 *     <App />
 *   </SpatialNavigationProvider>
 */
export function SpatialNavigationProvider({ children }) {
  // Load initial state from localStorage (default: enabled)
  const [enabled, setEnabled] = useState(() => {
    const stored = localStorage.getItem('spatialNavigationEnabled');
    return stored !== null ? stored === 'true' : true;
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
