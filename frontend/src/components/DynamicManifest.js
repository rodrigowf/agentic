import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Dynamically switches PWA manifest based on current route
 * Allows each page to be installed as a separate standalone app
 */
const DynamicManifest = () => {
  const location = useLocation();

  useEffect(() => {
    // Get existing manifest link or create new one
    let manifestLink = document.querySelector('link[rel="manifest"]');
    if (!manifestLink) {
      manifestLink = document.createElement('link');
      manifestLink.rel = 'manifest';
      document.head.appendChild(manifestLink);
    }

    // Determine manifest based on route
    const basePath = process.env.PUBLIC_URL || '';
    let manifestPath;

    if (location.pathname.includes('/mobile-voice')) {
      manifestPath = `${basePath}/manifest-mobile-voice.json`;
    } else if (location.pathname.includes('/voice')) {
      manifestPath = `${basePath}/manifest-voice.json`;
    } else if (location.pathname.includes('/agents')) {
      manifestPath = `${basePath}/manifest-agents.json`;
    } else {
      manifestPath = `${basePath}/manifest.json`;
    }

    manifestLink.href = manifestPath;

    // Update theme color for mobile browser chrome
    let themeColorMeta = document.querySelector('meta[name="theme-color"]');
    if (!themeColorMeta) {
      themeColorMeta = document.createElement('meta');
      themeColorMeta.name = 'theme-color';
      document.head.appendChild(themeColorMeta);
    }

    // Set theme color based on route
    if (location.pathname.includes('/mobile-voice')) {
      themeColorMeta.content = '#ff9800'; // Orange for mobile
    } else if (location.pathname.includes('/voice')) {
      themeColorMeta.content = '#4caf50'; // Green for voice
    } else if (location.pathname.includes('/agents')) {
      themeColorMeta.content = '#2196f3'; // Blue for agents
    } else {
      themeColorMeta.content = '#3f51b5'; // Default indigo
    }

  }, [location.pathname]);

  return null; // This component doesn't render anything
};

export default DynamicManifest;
