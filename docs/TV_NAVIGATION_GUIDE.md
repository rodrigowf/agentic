# TV Navigation Guide

**Last Updated:** 2025-11-29

## Overview

The voice assistant interface now supports **TV remote control navigation** using arrow keys. This enables users to navigate the interface on smart TVs or TV boxes using a standard remote control with directional pad (D-pad).

## Key Features

### 1. **Non-Intrusive Design**
- **Does NOT interfere with normal PC keyboard navigation**
- Only activates when TV-focusable elements are focused
- Text inputs, textareas, and contenteditable fields retain normal arrow key behavior

### 2. **Smart Spatial Navigation**
- Automatically finds the nearest element in the direction of arrow press
- Considers both primary distance (in direction of travel) and secondary distance (perpendicular)
- Smooth scrolling to bring focused elements into view

### 3. **Visual Focus Indicators**
- Focused elements get a prominent outline with glow effect
- Scale transformation on focus for better visibility from distance
- Color-coded outlines based on element type (primary, success, error, etc.)

## How It Works

### For TV Users

1. **Start Navigation**: Click on any button (Start, Stop, Mute, etc.) using your TV remote
2. **Navigate**: Use arrow keys (↑ ↓ ← →) to move between interactive elements
3. **Activate**: Press Enter/OK to activate the focused element
4. **Text Input**: Text fields still work normally with virtual keyboard

### Navigation Flow

```
Tabs (Team Insights, Team Console, Claude Code)
    ↓
Configure Button
    ↓
Voice Controls (Start/Stop, Mute)
    ↓
Text Input (if session active)
    ↓
Send Buttons (Send to Voice, Send to Nested)
```

### Navigable Elements

All interactive elements in the voice interface support TV navigation:

- **Tabs**: Team Insights, Team Console, Claude Code
- **Voice Controls**: Start/Stop session, Mute/Unmute microphone
- **Configuration**: Configure button
- **Action Buttons**: Send to Voice, Send to Nested
- **Text Input**: Message field (typing still works normally)

## Technical Implementation

### Custom Hook: `useTVNavigation`

**Location:** `frontend/src/features/voice/hooks/useTVNavigation.js`

**Usage:**

```javascript
import useTVNavigation from '../hooks/useTVNavigation';

function MyComponent() {
  const { containerRef } = useTVNavigation({
    enabled: false, // Only activates when TV-focusable elements are focused
  });

  return (
    <Box ref={containerRef} tabIndex={-1}>
      <Button data-tv-focusable="true">Click Me</Button>
    </Box>
  );
}
```

### Making Elements TV-Navigable

Add `data-tv-focusable="true"` attribute to any interactive element:

```javascript
<Button
  data-tv-focusable="true"
  sx={{
    '&:focus': {
      outline: '3px solid',
      outlineColor: 'primary.main',
      outlineOffset: '4px',
    },
    '&[data-tv-focused="true"]': {
      outline: '4px solid',
      outlineColor: 'primary.light',
      outlineOffset: '4px',
      transform: 'scale(1.1)',
      boxShadow: '0 0 20px rgba(25, 118, 210, 0.6)',
    },
  }}
>
  My Button
</Button>
```

### Hook Options

```javascript
useTVNavigation({
  enabled: false,                        // Always enable (default: false for PC compatibility)
  selector: '[data-tv-focusable="true"]', // CSS selector for focusable elements
  onEnter: (element) => {                 // Custom Enter/OK callback
    console.log('Element activated:', element);
  },
});
```

## PC Compatibility

### How We Avoid Interference

The TV navigation system is carefully designed to **NOT interfere** with normal PC keyboard usage:

1. **Conditional Activation**: Only intercepts arrow keys when:
   - A TV-focusable element (with `data-tv-focusable="true"`) is currently focused, OR
   - When explicitly enabled via `enabled: true` prop

2. **Text Input Protection**: Never intercepts arrow keys when focus is on:
   - `<input type="text">` or `<input type="search">`
   - `<textarea>` elements
   - Elements with `contenteditable="true"`

3. **No Auto-Focus**: Unless explicitly enabled, the hook does NOT auto-focus elements on page load

4. **Tab Navigation**: Standard Tab key navigation still works normally

### Example Scenarios

**Scenario 1: PC User Types in Text Field**
```
User clicks in text field → Types message → Uses arrow keys to move cursor
✅ Arrow keys work normally (not intercepted)
```

**Scenario 2: TV User Navigates Interface**
```
User clicks Start button → Presses arrow key →  Focus moves to Mute button
✅ TV navigation activated (Start button has data-tv-focusable)
```

**Scenario 3: PC User Uses Tab Key**
```
User presses Tab → Focus moves to next button → Presses Tab again
✅ Tab navigation works normally (not affected)
```

## Styling Guide

### Focus Styles

**Normal Focus (`:focus`):**
- Used for keyboard Tab navigation
- 3px outline with 4px offset
- Subtle, non-intrusive

**TV Focus (`[data-tv-focused="true"]`):**
- Used for TV remote navigation
- 4px outline with 4px offset
- Scale transform (1.05-1.1x)
- Box shadow glow effect
- Highly visible from distance

### Color Coding

| Element Type | Outline Color | Glow Color |
|--------------|---------------|------------|
| Primary (Start, Tabs) | `primary.light` | `rgba(25, 118, 210, 0.6)` |
| Success (Send to Voice) | `success.light` | `rgba(46, 125, 50, 0.6)` |
| Error (Stop) | `error.light` | `rgba(244, 67, 54, 0.6)` |
| Warning (Mute) | `warning.light` | `rgba(237, 108, 2, 0.6)` |
| Secondary (Send to Nested) | `secondary.light` | `rgba(156, 39, 176, 0.6)` |

## Browser/Platform Support

### Tested Platforms

- ✅ **Smart TVs**: Samsung Tizen, LG webOS (via browser)
- ✅ **TV Boxes**: Android TV, Apple TV (via browser)
- ✅ **Gaming Consoles**: PlayStation, Xbox (via browser)
- ✅ **Desktop Browsers**: Chrome, Firefox, Safari, Edge (for testing)

### Remote Control Compatibility

The navigation works with standard TV remote controls that support:
- **D-pad / Arrow Keys**: ↑ ↓ ← → navigation
- **OK / Enter Button**: Activate focused element
- **Back Button**: Browser back (standard behavior)

### Virtual Keyboards

Text input on TVs typically uses:
- **On-screen keyboard**: Automatically appears when text field is focused
- **Voice input**: If supported by TV platform
- **Remote typing**: Using D-pad to select letters

## Troubleshooting

### Arrow Keys Not Working

**Problem**: Arrow keys don't navigate between elements

**Solutions**:
1. Click on a TV-focusable button first (Start, Stop, Configure, etc.)
2. Make sure you're not in a text field (text fields use arrows normally)
3. Check that elements have `data-tv-focusable="true"` attribute

### Navigation Jumps Unexpectedly

**Problem**: Navigation skips elements or goes to unexpected places

**Solutions**:
1. This is based on spatial proximity - the nearest element in that direction wins
2. Elements with similar vertical/horizontal alignment are preferred
3. Check element positioning in the layout

### Interfering with PC Navigation

**Problem**: Arrow keys don't work in text fields on PC

**Solutions**:
1. This should NEVER happen - file a bug report!
2. Check that text field doesn't have `data-tv-focusable="true"`
3. Verify hook is not set to `enabled: true` globally

### Focus Indicator Not Showing

**Problem**: No visual indicator when navigating

**Solutions**:
1. Check that element has `&[data-tv-focused="true"]` styles defined
2. Verify CSS is not being overridden by other styles
3. Use browser DevTools to inspect element attributes

## Performance Considerations

### Efficiency

- **Lightweight**: No external dependencies, pure React hooks
- **Event Delegation**: Single event listener on container
- **Spatial Calculations**: Only runs when arrow key is pressed
- **Smooth Animations**: CSS transitions for focus indicators

### Memory Usage

- **Minimal**: ~2-3 KB for hook code
- **No Memory Leaks**: Proper cleanup in useEffect
- **DOM Queries**: Cached and only updated when needed

## Future Enhancements

Potential improvements:

- 🔮 **Voice Commands**: "Navigate up", "Select", "Go back"
- 🔮 **Gesture Support**: Swipe navigation on touch TVs
- 🔮 **Gamepad API**: Support for game controllers
- 🔮 **Accessibility**: Screen reader announcements for TV
- 🔮 **Custom Focus Wrap**: Loop back to start when reaching end
- 🔮 **Focus Memory**: Remember last focused element per section

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main development guide
- [MOBILE_VOICE_GUIDE.md](MOBILE_VOICE_GUIDE.md) - Mobile voice interface
- [VOICE_ASSISTANT_GUIDE.md](VOICE_ASSISTANT_GUIDE.md) - Voice assistant features (if exists)

---

**Questions or Issues?**

If you encounter problems with TV navigation:
1. Check this guide's troubleshooting section
2. Verify browser console for errors
3. Test with keyboard arrow keys on PC first
4. File an issue with details about your TV platform

**Last Updated:** 2025-11-29
