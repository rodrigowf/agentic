# Keyboard Navigation Guide

**Last Updated:** 2025-11-30
**Version:** 1.0.0

Complete guide to keyboard navigation and accessibility features in the Agentic application.

---

## Table of Contents

1. [Overview](#overview)
2. [Global Shortcuts](#global-shortcuts)
3. [Page-Specific Shortcuts](#page-specific-shortcuts)
4. [Accessibility Features](#accessibility-features)
5. [Implementation Details](#implementation-details)

---

## Overview

The Agentic application supports comprehensive keyboard navigation, allowing users to navigate and control the entire application without using a mouse. This improves:

- **Accessibility** - Screen reader support and keyboard-only navigation
- **Productivity** - Faster workflow with keyboard shortcuts
- **Usability** - Consistent experience across all pages

### Quick Start

- Press **Shift+?** to view all available keyboard shortcuts
- Use **Tab** to navigate between elements
- Use **Alt+1/2/3** to switch between main pages
- All buttons and controls have keyboard shortcuts

---

## Global Shortcuts

These shortcuts work from any page in the application:

| Shortcut | Action | Description |
|----------|--------|-------------|
| **Alt+1** | Go to Agents | Navigate to Agents page |
| **Alt+2** | Go to Tools | Navigate to Tools page |
| **Alt+3** | Go to Voice | Navigate to Voice page |
| **Shift+?** | Show Help | Display keyboard shortcuts help dialog |
| **Tab** | Next Element | Move focus to next interactive element |
| **Shift+Tab** | Previous Element | Move focus to previous interactive element |
| **Escape** | Close Dialog | Close any open dialog or modal |
| **Enter** | Activate | Activate the focused button or link |
| **Space** | Toggle | Toggle checkboxes, switches, or buttons |

---

## Page-Specific Shortcuts

### Agents Page

**Navigation:**
- **↑** - Move up in agent list
- **↓** - Move down in agent list
- **Enter** - Select highlighted agent
- **Tab** - Switch between list, editor, and console panels

**Agent Console:**
- **Ctrl+R** - Run agent with current task
- **Ctrl+X** - Stop running agent
- **Ctrl+Shift+L** - Clear console logs
- **Enter** (in task field) - Focus on Run button

**Features:**
- Agent list has visual focus indicators
- Arrow key navigation updates selection
- Mouse hover also updates selection for hybrid navigation

### Voice Page

**Voice Controls:**
- **Ctrl+S** - Start/Stop voice session
- **Ctrl+M** - Toggle microphone mute
- **Ctrl+K** - Toggle speaker mute

**Features:**
- Voice controls work even when not focused
- Visual feedback for all state changes
- Keyboard shortcuts shown in tooltips

### Tools Page

**Standard Navigation:**
- **Tab** - Navigate between tools
- **Enter** - Open/edit selected tool
- **Ctrl+S** - Save tool (when editing)

---

## Accessibility Features

### Visual Focus Indicators

All interactive elements have clear visual focus indicators:

- **Buttons** - 3px solid outline with offset
- **Form fields** - 2px solid outline
- **Navigation items** - Highlighted background and border
- **List items** - Outline and background change

**Color Scheme:**
- Light mode: Blue (#3f51b5)
- Dark mode: Light blue (#90caf9)

### Skip to Main Content

- Press **Tab** immediately after page load
- Activates "Skip to main content" link
- Jumps directly to main content area
- Bypasses navigation for screen readers

### ARIA Labels

All interactive elements include:
- **aria-label** - Descriptive labels for screen readers
- **aria-current** - Current page indicator
- **role** attributes - Semantic HTML roles
- **Tooltips** - Keyboard shortcut hints

### Screen Reader Support

- Semantic HTML structure
- Proper heading hierarchy
- Form label associations
- Status announcements
- Live region updates

---

## Implementation Details

### Architecture

**Files:**
- [/frontend/src/hooks/useKeyboardNavigation.js](frontend/src/hooks/useKeyboardNavigation.js) - Main keyboard hook
- [/frontend/src/shared/components/KeyboardShortcutsHelp.js](frontend/src/shared/components/KeyboardShortcutsHelp.js) - Help dialog
- [/frontend/src/App.js](frontend/src/App.js) - Global shortcuts and focus styles

### useKeyboardNavigation Hook

Custom React hook for managing keyboard shortcuts:

```javascript
import useKeyboardNavigation from '../hooks/useKeyboardNavigation';

// In your component
useKeyboardNavigation({
  shortcuts: {
    VOICE_START_STOP: () => toggleVoiceSession(),
    VOICE_MUTE: () => toggleMute(),
  },
  enabled: true,
  onHelp: () => setShowHelpDialog(true),
});
```

**Parameters:**
- `shortcuts` - Object mapping shortcut names to handler functions
- `enabled` - Enable/disable keyboard shortcuts
- `onHelp` - Callback when help shortcut is pressed

### Focus Management

**Global Styles (App.js):**

```css
/* All interactive elements */
*:focus-visible {
  outline: 3px solid #90caf9 !important;
  outline-offset: 2px !important;
}

/* Remove outline for mouse users */
*:focus:not(:focus-visible) {
  outline: none !important;
}

/* Form controls */
input:focus, textarea:focus, select:focus {
  outline: 2px solid #90caf9 !important;
  outline-offset: 2px !important;
}
```

### List Navigation

AgentDashboard example:

```javascript
// Track selected index
const [selectedIndex, setSelectedIndex] = useState(-1);

// Keyboard handler
useEffect(() => {
  const handleKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (items[selectedIndex]) navigate(items[selectedIndex].path);
        break;
    }
  };

  listElement.addEventListener('keydown', handleKeyDown);
  return () => listElement.removeEventListener('keydown', handleKeyDown);
}, [selectedIndex, items]);
```

### Adding New Shortcuts

**Step 1:** Add to KEYBOARD_SHORTCUTS configuration

```javascript
// In useKeyboardNavigation.js
export const KEYBOARD_SHORTCUTS = {
  // ... existing shortcuts
  MY_NEW_SHORTCUT: {
    key: 'n',
    ctrl: true,
    description: 'Create new item'
  },
};
```

**Step 2:** Add handler in component

```javascript
useKeyboardNavigation({
  shortcuts: {
    MY_NEW_SHORTCUT: () => {
      createNewItem();
    },
  },
  enabled: true,
});
```

**Step 3:** Update help dialog (automatic)

The KeyboardShortcutsHelp component automatically displays all shortcuts from the KEYBOARD_SHORTCUTS configuration.

---

## Testing Keyboard Navigation

### Manual Testing Checklist

**Global Navigation:**
- [ ] Alt+1/2/3 switches pages correctly
- [ ] Shift+? opens help dialog
- [ ] Tab cycles through all interactive elements
- [ ] Shift+Tab cycles backwards
- [ ] Escape closes dialogs

**Agents Page:**
- [ ] Arrow keys navigate agent list
- [ ] Enter selects agent
- [ ] Ctrl+R runs agent
- [ ] Ctrl+X stops running agent
- [ ] Ctrl+Shift+L clears logs

**Voice Page:**
- [ ] Ctrl+S starts/stops session
- [ ] Ctrl+M toggles microphone
- [ ] Ctrl+K toggles speaker

**Accessibility:**
- [ ] Skip to main content works
- [ ] All buttons have visible focus
- [ ] Form fields have visible focus
- [ ] Screen reader announces states
- [ ] Tooltips show keyboard shortcuts

### Browser Testing

Tested and working on:
- ✅ Chrome 120+ (Linux, Windows, macOS)
- ✅ Firefox 121+ (Linux, Windows, macOS)
- ✅ Safari 17+ (macOS)
- ✅ Edge 120+ (Windows)

### Screen Reader Testing

Tested with:
- ✅ NVDA (Windows)
- ✅ JAWS (Windows)
- ✅ VoiceOver (macOS, iOS)
- ✅ TalkBack (Android)

---

## Troubleshooting

### Shortcuts Not Working

**Issue:** Keyboard shortcuts don't trigger actions

**Solutions:**
1. Check if another element has focus (click on the page first)
2. Verify the component has `useKeyboardNavigation` hook enabled
3. Check browser console for errors
4. Ensure shortcuts don't conflict with browser shortcuts

### Focus Not Visible

**Issue:** Can't see which element has focus

**Solutions:**
1. Check if global focus styles are loaded
2. Verify browser supports :focus-visible
3. Try different keyboard (some keyboards may not trigger :focus-visible)
4. Check theme mode (focus colors change with light/dark)

### Tab Navigation Skips Elements

**Issue:** Tab key skips some interactive elements

**Solutions:**
1. Verify elements have tabIndex={0} or are naturally focusable
2. Check if elements are disabled
3. Ensure elements are visible (display: none removes from tab order)
4. Check for custom focus trap implementations

---

## Future Enhancements

Planned improvements:

- 🔮 **Custom Shortcut Configuration** - Allow users to customize shortcuts
- 🔮 **Shortcut Cheat Sheet** - Persistent on-screen shortcut reference
- 🔮 **Command Palette** - Ctrl+K command palette (like VS Code)
- 🔮 **Vim Mode** - Optional Vim-style navigation
- 🔮 **Voice Commands** - Trigger shortcuts via voice
- 🔮 **Gamepad Support** - Navigate with game controller

---

## Resources

### External Documentation

- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN: Keyboard-navigable JavaScript widgets](https://developer.mozilla.org/en-US/docs/Web/Accessibility/Keyboard-navigable_JavaScript_widgets)
- [WebAIM: Keyboard Accessibility](https://webaim.org/techniques/keyboard/)
- [A11y Project: Keyboard Navigation](https://www.a11yproject.com/checklist/#keyboard)

### Internal Documentation

- [CLAUDE.md](../CLAUDE.md) - Complete development guide
- [Frontend Architecture](FRONTEND_REFACTORING.md) - Component structure

---

## Changelog

### Version 1.0.0 (2025-11-30)

**Initial Release:**
- ✅ Global keyboard shortcuts (Alt+1/2/3, Shift+?)
- ✅ Agent list navigation (arrow keys)
- ✅ Agent console shortcuts (Ctrl+R/X/Shift+L)
- ✅ Voice controls (Ctrl+S/M/K)
- ✅ Focus indicators for all elements
- ✅ ARIA labels and semantic HTML
- ✅ Skip to main content link
- ✅ Keyboard shortcuts help dialog
- ✅ Screen reader support

---

**End of Keyboard Navigation Guide**

For questions or suggestions, create an issue in the repository.
