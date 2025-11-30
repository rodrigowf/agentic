import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * KeyboardNavigationProvider - Enables global keyboard navigation shortcuts
 * Must be inside Router context
 */
export default function KeyboardNavigationProvider() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (event) => {
      const { key, altKey, ctrlKey, shiftKey, metaKey } = event;

      // Check for global navigation shortcuts
      if (altKey && !ctrlKey && !shiftKey && !metaKey) {
        switch (key) {
          case '1':
            event.preventDefault();
            navigate('/');
            break;
          case '2':
            event.preventDefault();
            navigate('/tools');
            break;
          case '3':
            event.preventDefault();
            navigate('/voice');
            break;
          default:
            break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [navigate]);

  // This component doesn't render anything
  return null;
}
