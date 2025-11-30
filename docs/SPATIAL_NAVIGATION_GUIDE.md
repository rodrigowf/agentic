# Spatial Navigation Guide

## Overview

The application now includes **TV-remote-style spatial navigation** that allows users to navigate through all interactive elements using arrow keys. This feature is particularly useful for:

- **TV/WebView interfaces** (e.g., smart TVs, set-top boxes)
- **Accessibility** (keyboard-only users)
- **Power users** who prefer keyboard navigation
- **Testing and automation**

## How It Works

The spatial navigation system automatically detects all focusable elements on the page and allows you to move between them using the arrow keys (↑ ↓ ← →).

### Algorithm

When you press an arrow key:

1. **Direction Detection**: The system identifies the direction (up, down, left, right)
2. **Candidate Filtering**: Finds all focusable elements in that direction
3. **Distance Calculation**: Calculates the distance from the current element to each candidate
4. **Best Match Selection**: Selects the closest element using a weighted scoring system:
   - **Primary distance** (in the arrow direction): 100% weight
   - **Secondary distance** (perpendicular): 30% weight
5. **Focus & Scroll**: Focuses the best match and smoothly scrolls it into view

### Focusable Elements

The navigation system automatically includes:
- Buttons (`<button>`)
- Links (`<a href="...">`)
- Form inputs (`<input>`, `<select>`, `<textarea>`)
- Elements with `tabindex` (except `tabindex="-1"`)
- **Excludes**: Disabled elements, hidden elements, `aria-hidden="true"` containers

## Features

### 1. **Automatic Element Detection**
All focusable elements are automatically detected without any code changes to individual components.

### 2. **Spatial Awareness**
The algorithm considers 2D positioning - not just sequential tab order. This makes navigation feel natural and intuitive.

### 3. **Smooth Scrolling**
When navigating to an off-screen element, the page smoothly scrolls it into view.

### 4. **Persistent State**
Navigation preference is saved to `localStorage` and persists across sessions.

### 5. **Works Everywhere**
Navigation works across all pages:
- Agents Dashboard
- Tools Dashboard
- Voice Assistant
- Agent Editor
- Run Console

### 6. **No Breaking Changes**
Spatial navigation runs alongside existing keyboard shortcuts (Alt+1/2/3, Ctrl+S, etc.) without conflicts.

## Usage

### For Users

**Arrow Keys Navigation:**
- `↑` Up Arrow - Move to element above
- `↓` Down Arrow - Move to element below
- `←` Left Arrow - Move to element on the left
- `→` Right Arrow - Move to element on the right

**First Focus:**
If no element is focused, pressing any arrow key will focus the first focusable element on the page.

**Visual Feedback:**
Focused elements show a clear blue outline (customized in App.js global styles).

### For Developers

**Enabling/Disabling:**

The spatial navigation is enabled by default. To toggle it programmatically:

```javascript
import { useSpatialNavigationContext } from './components/SpatialNavigationProvider';

function MyComponent() {
  const { enabled, toggleEnabled } = useSpatialNavigationContext();

  return (
    <div>
      <p>Spatial Navigation: {enabled ? 'ON' : 'OFF'}</p>
      <button onClick={toggleEnabled}>
        Toggle Spatial Navigation
      </button>
    </div>
  );
}
```

**Excluding Elements:**

To exclude specific elements from spatial navigation, add the class `.spatial-nav-exclude`:

```javascript
<div className="spatial-nav-exclude">
  <button>This button won't be navigable via arrow keys</button>
</div>
```

**Custom Selector:**

The default selector targets:
```javascript
'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
```

To customize, modify `useSpatialNavigation` hook parameters in `SpatialNavigationProvider.js`.

## Architecture

### Files

1. **`frontend/src/hooks/useSpatialNavigation.js`**
   - Core spatial navigation logic
   - Element detection and scoring algorithm
   - Keyboard event handling

2. **`frontend/src/components/SpatialNavigationProvider.js`**
   - React context provider
   - State management (enabled/disabled)
   - localStorage persistence
   - Wraps the entire app

3. **`frontend/src/App.js`**
   - Integration point
   - Global focus styles (`:focus-visible` outline)

### Data Flow

```
User presses arrow key
    ↓
useSpatialNavigation hook receives keydown event
    ↓
getFocusableElements() - Query all eligible elements
    ↓
findBestCandidate() - Score and rank candidates
    ↓
Focus best element + scroll into view
```

## Configuration

### Customization Options

In `SpatialNavigationProvider.js`, you can configure:

```javascript
useSpatialNavigation({
  enabled: true,           // Enable/disable navigation
  loop: false,             // Whether to wrap around (e.g., from last to first)
  selector: '...',         // Custom CSS selector for focusable elements
  excludeSelector: '...',  // Selector for elements to exclude
});
```

### Loop Navigation

Currently, `loop` is set to `false`. If you want wrap-around navigation (e.g., pressing ↓ on the last element goes to the first), set `loop: true`.

## Best Practices

### For Component Authors

1. **Use Semantic HTML**: Prefer `<button>` over `<div onClick>` - buttons are automatically focusable
2. **Accessible Labels**: Ensure all interactive elements have clear `aria-label` or visible text
3. **Logical Layout**: Arrange elements in a logical spatial order (top-to-bottom, left-to-right)
4. **Test with Keyboard**: Navigate your component using only arrow keys to verify UX

### For Testing

1. **Initial Focus**: Always test what happens when the page first loads (first arrow press)
2. **Scrolling**: Test navigation with off-screen elements
3. **Dense Layouts**: Test with many elements close together
4. **Empty States**: Test with no focusable elements (e.g., loading states)

## Accessibility

The spatial navigation system is designed with accessibility in mind:

- **Focus Indicators**: Clear `:focus-visible` outlines (3px blue, 2px offset)
- **Screen Reader Support**: Works alongside ARIA labels and roles
- **No Mouse Required**: Fully keyboard-navigable
- **Skip to Main Content**: Existing skip link still works

### WCAG Compliance

- **2.1.1 Keyboard**: All functionality is keyboard accessible ✓
- **2.4.7 Focus Visible**: Clear focus indicators on all elements ✓
- **2.4.3 Focus Order**: Spatial algorithm respects logical visual order ✓

## Troubleshooting

### Issue: Navigation not working

**Check:**
1. Is spatial navigation enabled? Check localStorage: `localStorage.getItem('spatialNavigationEnabled')`
2. Are there focusable elements on the page?
3. Check browser console for errors

### Issue: Wrong element gets focused

**Possible causes:**
1. Elements are visually close but spatially far (check coordinates)
2. Hidden elements are being detected (add `.spatial-nav-exclude`)
3. Layout shifts between detection and focus

**Solution:**
Adjust the scoring algorithm in `useSpatialNavigation.js` (line ~95):
```javascript
const score = primaryDist + (secondaryDist * 0.3); // Adjust 0.3 to change perpendicular weight
```

### Issue: Elements outside viewport

**Solution:**
The system automatically scrolls elements into view with `scrollIntoView()`. If not working, check:
- Element is not `position: fixed` (may need custom handling)
- Parent containers allow overflow scrolling

## Future Enhancements

Potential improvements:

- [ ] **Focus memory**: Remember last focused element per page
- [ ] **Navigation zones**: Group elements into navigable sections
- [ ] **Visual preview**: Show which element will be focused before navigation
- [ ] **Customizable keybindings**: Allow users to remap arrow keys
- [ ] **Navigation history**: Back/forward navigation (Backspace/Shift+Backspace)
- [ ] **Smart loop**: Automatically detect boundaries and enable loop per-section

## Related Documentation

- [Keyboard Shortcuts](../shared/components/KeyboardShortcutsHelp.js) - All app keyboard shortcuts
- [Accessibility Guide](./ACCESSIBILITY.md) - Full accessibility documentation (future)
- [TV WebView Guide](./TV_WEBVIEW_FIX_SUMMARY.md) - TV deployment notes

## Credits

Implemented: 2025-11-30
Based on: TV remote navigation patterns, Smart TV UX best practices
