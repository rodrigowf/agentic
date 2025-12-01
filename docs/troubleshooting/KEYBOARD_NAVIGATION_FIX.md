# Keyboard Navigation Router Context Fix

**Date:** 2025-11-30
**Issue:** `useNavigate() may be used only in the context of a <Router> component` error

## Problem

The `useKeyboardNavigation` hook was being called in `App.js` before the `<Router>` component was rendered, causing a React Router context error:

```
Error: useNavigate() may be used only in the context of a <Router> component.
    at useKeyboardNavigation (useKeyboardNavigation.js:42:1)
    at App (App.js:91:1)
```

## Root Cause

React hooks like `useNavigate()` cannot be called outside of their provider context. The app structure was:

```jsx
function App() {
  // ❌ This hook calls useNavigate() before Router exists
  useKeyboardNavigation({ enabled: true });

  return (
    <Router>
      {/* Router content */}
    </Router>
  );
}
```

## Solution

Split keyboard navigation into two parts:

### 1. Created KeyboardNavigationProvider Component

**File:** `frontend/src/components/KeyboardNavigationProvider.js`

A separate component that handles page navigation shortcuts (Alt+1/2/3) and runs **inside** the Router context:

```jsx
export default function KeyboardNavigationProvider() {
  const navigate = useNavigate(); // ✅ Inside Router context

  useEffect(() => {
    const handleKeyDown = (event) => {
      const { key, altKey, ctrlKey, shiftKey, metaKey } = event;

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
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  return null; // Doesn't render anything
}
```

### 2. Updated useKeyboardNavigation Hook

**File:** `frontend/src/hooks/useKeyboardNavigation.js`

Removed the `useNavigate()` call and page navigation logic:

```javascript
// Before (❌ broken):
export default function useKeyboardNavigation({ ... }) {
  const navigate = useNavigate(); // ❌ Error if not in Router
  // ...
}

// After (✅ fixed):
export default function useKeyboardNavigation({ ... }) {
  // No useNavigate() call
  // Only handles help shortcut and custom shortcuts
  // ...
}
```

### 3. Updated App.js

**File:** `frontend/src/App.js`

Added `KeyboardNavigationProvider` inside the Router:

```jsx
function App() {
  // ✅ Hook no longer calls useNavigate()
  useKeyboardNavigation({
    enabled: true,
    onHelp: () => setShowKeyboardHelp(true),
  });

  return (
    <Router basename={process.env.PUBLIC_URL || ''}>
      {/* ✅ Navigation shortcuts enabled inside Router */}
      <KeyboardNavigationProvider />

      <Routes>
        {/* ... */}
      </Routes>
    </Router>
  );
}
```

## Architecture After Fix

```
App Component (outside Router)
├── useKeyboardNavigation (Shift+? help shortcut only)
└── Router
    ├── KeyboardNavigationProvider (Alt+1/2/3 page navigation)
    └── Routes
        ├── AgentDashboard (with keyboard shortcuts)
        ├── VoiceAssistant (with keyboard shortcuts)
        └── ...
```

## Files Changed

1. **Created:** `frontend/src/components/KeyboardNavigationProvider.js`
   - New component for page navigation shortcuts
   - Must be inside Router context

2. **Modified:** `frontend/src/hooks/useKeyboardNavigation.js`
   - Removed `useNavigate()` import and usage
   - Removed page navigation logic
   - Only handles help and custom shortcuts

3. **Modified:** `frontend/src/App.js`
   - Added import for `KeyboardNavigationProvider`
   - Added provider component inside Router
   - Updated comments to clarify responsibility split

## Keyboard Shortcuts Still Working

All keyboard shortcuts continue to work as expected:

**Global Shortcuts:**
- ✅ **Alt+1/2/3** - Page navigation (via KeyboardNavigationProvider)
- ✅ **Shift+?** - Help dialog (via useKeyboardNavigation)

**Page-Specific Shortcuts:**
- ✅ **Ctrl+S/M/K** - Voice controls (VoiceAssistant)
- ✅ **Ctrl+R/X** - Agent run/stop (RunConsole)
- ✅ **Arrow keys** - Agent list navigation (AgentDashboard)
- ✅ **Tab/Shift+Tab** - Focus navigation (everywhere)

## Testing

**Build Status:**
```bash
npm run build
# ✅ Compiled successfully
# File sizes after gzip:
#   479.82 kB  build/static/js/main.1109295d.js
```

**Runtime:**
- ✅ No console errors
- ✅ All keyboard shortcuts working
- ✅ Router context available where needed

## Lessons Learned

1. **React Hooks Rules:** Hooks that require context (like `useNavigate`) must be called inside that context
2. **Component Separation:** Split functionality based on context requirements
3. **Provider Pattern:** Use invisible provider components for global event handlers
4. **Hook Responsibilities:** Keep hooks focused on one concern

## Related Documentation

- [Keyboard Navigation Guide](KEYBOARD_NAVIGATION_GUIDE.md) - Complete usage guide
- [React Router Docs](https://reactrouter.com/en/main/hooks/use-navigate) - useNavigate hook

---

**Status:** ✅ Fixed and deployed
**Build:** ✅ Successful
**Runtime:** ✅ No errors
