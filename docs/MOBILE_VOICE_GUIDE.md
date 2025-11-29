# Mobile Voice Interface Guide

**Last Updated:** 2025-11-28

## Overview

The Mobile Voice interface allows you to use your smartphone as a **wireless microphone** for voice conversations running on your desktop computer. This creates a seamless multi-device experience where you can move around while staying connected to your AI assistant.

---

## Quick Start

### 1. **Start a Voice Conversation on Desktop**

1. Open the desktop browser: `http://localhost:3000/voice`
2. Create or select a conversation
3. Start the voice session (this will be your main interface)

### 2. **Connect Your Mobile Device**

1. Get your computer's IP address:
   ```bash
   # On Linux/Mac
   hostname -I
   # or
   ifconfig | grep "inet "

   # On Windows
   ipconfig
   ```

2. On your Android Chrome browser, navigate to:
   ```
   http://[YOUR_IP]:3000/mobile-voice
   ```
   Example: `http://192.168.1.100:3000/mobile-voice`

3. Select the active conversation from the dropdown

4. Tap the **green play button** to start

5. You'll start **muted** - tap the microphone button to unmute and start speaking

---

## Features

### **Conversation Selector**
- **Dropdown at the top** shows all available voice conversations
- **Auto-selects** if there's only one active conversation
- **Disabled during session** - select before starting
- Updates every 10 seconds to show new conversations

### **Voice Controls**

#### Start/Stop Button (Large, center)
- **Green Play Icon**: Tap to connect to the voice session
- **Red Stop Icon**: Tap to disconnect (pulses when active)

#### Mute/Unmute Button (Below start/stop)
- **Orange Mic-Off Icon**: Currently muted (default state)
- **Green Mic Icon**: Currently unmuted and listening
- Tap to toggle between muted/unmuted
- **Starts muted by default** to prevent accidental audio

### **Audio Visualization**

Two separate level meters:

1. **Microphone Level** (Green/Gray)
   - Shows your voice input level
   - Green when unmuted, gray when muted
   - Real-time feedback of your speech

2. **Speaker Level** (Blue)
   - Shows AI assistant voice output
   - Independent of your microphone
   - Indicates when the AI is speaking

### **Recent Activity**

Bottom section shows latest events:
- Team agent messages
- Tool usage
- Claude Code activity
- Automatically scrolls to show most recent

### **Status Indicators**

- **"Desktop session is active"** - Another device is connected
- **Connection status** - Connected/Idle
- **Conversation info** - Shows selected conversation name

---

## Usage Scenarios

### **Scenario 1: Mobile as Remote Mic**

Perfect for walking around while talking to your AI:

1. Desktop shows full interface (team insights, code changes, console)
2. Mobile is just your wireless microphone
3. Speak into phone, hear AI response on both devices
4. Mute mobile when near desktop to avoid echo

### **Scenario 2: Privacy in Shared Spaces**

Keep work private while in public:

1. Desktop at home with headphones
2. Mobile in hand while walking
3. Speak quietly into phone
4. Only you hear responses (use phone headphones)

### **Scenario 3: Multi-Room Collaboration**

Switch locations seamlessly:

1. Start conversation at desk
2. Move to another room with mobile
3. Return to desk, mobile auto-detects active session
4. No interruption in conversation flow

---

## Technical Details

### **How It Works**

1. **Each device** creates its own WebRTC connection to OpenAI
2. **Same conversation_id** means shared event history
3. **Independent audio streams** - each device has own mic/speaker
4. **Synchronized state** via WebSocket event broadcasting
5. **No backend changes needed** - uses existing infrastructure

### **Network Requirements**

- **Same WiFi network** as the backend server
- **Backend accessible** at `http://[IP]:8000`
- **Frontend accessible** at `http://[IP]:3000`
- **WebRTC** requires UDP ports (handled automatically)

### **Browser Compatibility**

Tested on:
- ✅ Android Chrome (primary target)
- ✅ Android Firefox
- ⚠️ iOS Safari (may have WebRTC limitations)

### **Audio Processing**

- **Sample Rate**: 24kHz (OpenAI Realtime API default)
- **Format**: Opus codec via WebRTC
- **Latency**: ~200-500ms (network dependent)
- **Echo Cancellation**: Built into WebRTC

---

## Tips & Best Practices

### ✅ **Do:**

- **Start muted** (default) to avoid accidental recording
- **Use headphones** on desktop if mobile is in same room
- **Check WiFi signal** before starting long conversations
- **Select conversation first** before tapping play
- **Keep screen on** (mobile may disconnect if screen sleeps)

### ❌ **Don't:**

- Have both devices unmuted in the same room (echo!)
- Switch conversations mid-session (stop first)
- Expect low latency over cellular data (use WiFi)
- Leave mobile unattended while connected (battery drain)

---

## Troubleshooting

### **Problem: "No conversations available"**

**Solution:**
1. Check desktop has at least one conversation created
2. Verify mobile can reach backend (try `http://[IP]:8000/api/realtime/conversations`)
3. Refresh the mobile page

### **Problem: "Failed to fetch token"**

**Solution:**
1. Backend not running or not accessible
2. Check `OPENAI_API_KEY` is set in backend `.env`
3. Verify network connectivity (`ping [IP]`)

### **Problem: Echo or feedback**

**Solution:**
1. Mute mobile mic when near desktop speakers
2. Use headphones on desktop
3. Or use only one device's microphone at a time

### **Problem: Disconnects frequently**

**Solution:**
1. Check WiFi signal strength
2. Disable battery optimization for browser
3. Keep mobile screen on
4. Use power-saving mode: stop session when not actively speaking

### **Problem: High latency (delayed responses)**

**Solution:**
1. Switch to WiFi (don't use cellular)
2. Check for network congestion
3. Move closer to WiFi router
4. Reduce other network usage

### **Problem: Can't hear AI responses**

**Solution:**
1. Check mobile volume (not muted)
2. Check audio element permissions in browser
3. Try stopping and restarting session
4. Verify desktop session is sending audio

---

## Mobile-Specific Optimizations

### **Battery Saving**

The mobile interface is designed for efficiency:
- Minimal UI (low CPU usage)
- No video rendering
- Efficient audio processing
- Stop session when idle

**Estimated battery drain**: ~10-15% per hour of active conversation

### **Data Usage**

Over WiFi (recommended):
- **Bidirectional audio**: ~40-60 KB/s
- **Event stream**: ~1-5 KB/s
- **Total**: ~50-70 KB/s (~200 MB/hour)

Over cellular (not recommended):
- Same bandwidth, but higher latency
- May incur data charges
- WebRTC quality degrades on poor connections

### **Screen Settings**

To prevent disconnections:

**Android:**
1. Settings → Display → Screen timeout
2. Set to "10 minutes" or higher
3. Or use "Keep screen on" developer option

**Alternative:**
- Use "Caffeine" or similar keep-awake apps
- Or periodically tap screen to prevent sleep

---

## Advanced Configuration

### **Custom Backend URL**

If running backend on different port/host:

1. Set environment variable before starting frontend:
   ```bash
   REACT_APP_BACKEND_URL=http://192.168.1.100:8000 npm start
   ```

2. Or edit `frontend/.env`:
   ```
   REACT_APP_BACKEND_URL=http://192.168.1.100:8000
   ```

### **Multiple Mobile Devices**

You can connect **multiple mobiles** to the same conversation:

1. Each gets independent mic/speaker
2. All share same event history
3. All can speak (though AI processes one at a time)
4. Use case: Multiple people in different rooms

### **Desktop + Mobile Simultaneous Use**

Both can be unmuted, but be aware:
- Risk of echo if in same room
- AI may get confused by overlapping speech
- Recommended: Use only one mic at a time
- Use visual indicators to coordinate who's speaking

---

## Security Considerations

### **Network Exposure**

When accessing mobile interface:
- Backend is exposed on local network
- Use firewall rules to restrict access if needed
- Consider VPN for remote access (not recommended for real-time)

### **Audio Privacy**

- Audio streams go directly to OpenAI (not stored on backend)
- Conversation events are stored in local SQLite database
- Mute when not actively conversing
- Stop session when done to prevent accidental recording

---

## Roadmap / Future Enhancements

Potential improvements (not yet implemented):

- 🔮 **QR Code Join**: Desktop shows QR code to quickly join from mobile
- 🔮 **Push-to-Talk**: Hold button to speak (saves battery)
- 🔮 **Voice Activity Detection**: Auto-mute when silent
- 🔮 **Connection Quality Indicator**: Show latency/packet loss
- 🔮 **Offline Buffering**: Queue messages during brief disconnects
- 🔮 **Multi-language UI**: i18n support

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Complete project architecture
- [Voice Assistant System](../CLAUDE.md#voice-assistant-system) - Desktop voice interface
- [API Documentation](../backend/docs/) - Backend API reference

---

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review browser console for errors (Chrome DevTools)
3. Check backend logs: `uvicorn main:app --reload --log-level debug`
4. File issue on GitHub repository

---

**Happy multi-device AI conversations! 🎙️📱💻**
