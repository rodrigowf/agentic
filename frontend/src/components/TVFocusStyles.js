import { useSpatialNavigationContext } from './SpatialNavigationProvider';

/**
 * TVFocusStyles - Injects heavy focus outline styles only on TV
 *
 * On TV (Fire TV, Android TV), we need prominent focus indicators
 * for remote navigation. On desktop/mobile, we use subtle defaults.
 */
export default function TVFocusStyles({ mode }) {
  const { isTV } = useSpatialNavigationContext();

  if (!isTV) {
    return null;
  }

  // Only render heavy focus styles on TV
  return (
    <style>
      {`
        /* TV-specific: Heavy focus styling for remote navigation */
        *:focus-visible {
          outline: 3px solid ${mode === 'dark' ? '#90caf9' : '#3f51b5'} !important;
          outline-offset: 2px !important;
        }

        /* TV-specific: Form control focus */
        input:focus,
        textarea:focus,
        select:focus {
          outline: 2px solid ${mode === 'dark' ? '#90caf9' : '#3f51b5'} !important;
          outline-offset: 2px !important;
        }

        /* TV-specific: Focus styles for interactive elements */
        button:focus-visible,
        a:focus-visible {
          outline: 3px solid ${mode === 'dark' ? '#90caf9' : '#3f51b5'} !important;
          outline-offset: 3px !important;
          transition: outline 0.2s ease;
        }
      `}
    </style>
  );
}
