import { useRef, useCallback } from 'react';

/**
 * Audio mixing for desktop + mobile microphones
 * Creates a mixed audio stream that combines desktop mic and mobile mic
 */
export const useAudioMixer = ({ recordEvent }) => {
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const mixerDestinationRef = useRef(null);
  const desktopSourceRef = useRef(null);
  const mobileAudioSourceRef = useRef(null);
  const mobileGainNodeRef = useRef(null);
  const desktopGainNodeRef = useRef(null);

  /**
   * Initialize audio mixer with desktop microphone
   * @returns {Promise<Object>} { audioContext, mixerStream, micStream, hasMicrophone }
   */
  const initializeMixer = useCallback(async () => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioContextRef.current = audioContext;
    console.log('[AudioMixer] Initializing AudioContext - sampleRate:', audioContext.sampleRate);

    // Try to get desktop microphone
    let micStream = null;
    let hasMicrophone = false;

    try {
      console.log('[AudioMixer] Requesting getUserMedia audio constraints: { audio: true }');
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = micStream;
      hasMicrophone = true;
      console.log('[AudioMixer] Desktop microphone acquired successfully, track count:', micStream.getTracks().length);
      const track = micStream.getAudioTracks()[0];
      if (track) {
        console.log('[AudioMixer] Mic track settings:', track.getSettings());
        console.log('[AudioMixer] Mic track constraints:', track.getConstraints());
        track.onended = () => console.warn('[AudioMixer] Mic track ended');
        track.onmute = () => console.warn('[AudioMixer] Mic track muted');
        track.onunmute = () => console.warn('[AudioMixer] Mic track unmuted');
      }
    } catch (micError) {
      console.warn('[AudioMixer] No microphone available, creating silent audio stream:', micError.message);
      // Create silent stream as fallback
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      gainNode.gain.value = 0; // Silent
      oscillator.connect(gainNode);
      const silentDestination = audioContext.createMediaStreamDestination();
      gainNode.connect(silentDestination);
      oscillator.start();
      micStream = silentDestination.stream;
      micStreamRef.current = micStream;
      hasMicrophone = false;

      // Record no-mic mode
      void recordEvent('controller', 'session_started_without_microphone', {
        message: 'Session started without desktop microphone - mobile microphone required',
        error: micError.message,
      });
    }

    // Create mixer destination
    const mixerDestination = audioContext.createMediaStreamDestination();
    mixerDestinationRef.current = mixerDestination;

    // Desktop gain node
    const desktopGain = audioContext.createGain();
    const desktopSource = audioContext.createMediaStreamSource(micStream);
    desktopSource.connect(desktopGain);
    desktopGain.connect(mixerDestination);
    desktopGain.gain.value = hasMicrophone ? 1.0 : 0.0; // Mute if no real mic
    console.log('[AudioMixer] Desktop gain initialized:', desktopGain.gain.value);

    // Store desktop source for mute control
    desktopSourceRef.current = { source: desktopSource, gain: desktopGain, hasMicrophone };

    // Mobile gain node (will be connected when mobile joins)
    const mobileGain = audioContext.createGain();
    mobileGainNodeRef.current = mobileGain;
    mobileGain.connect(mixerDestination);
    mobileGain.gain.value = 1.0;
    console.log('[AudioMixer] Mixer destination tracks:', mixerDestination.stream.getTracks().length);

    return {
      audioContext,
      mixerStream: mixerDestination.stream,
      micStream,
      hasMicrophone,
    };
  }, [recordEvent]);

  /**
   * Toggle desktop microphone mute
   */
  const toggleDesktopMute = useCallback((newMutedState) => {
    if (desktopSourceRef.current && desktopSourceRef.current.gain) {
      if (desktopSourceRef.current.hasMicrophone) {
        desktopSourceRef.current.gain.gain.value = newMutedState ? 0.0 : 1.0;
        console.log('[AudioMixer] Desktop mic gain set to:', newMutedState ? 0.0 : 1.0);
      } else {
        console.log('[AudioMixer] No desktop microphone - mute button has no effect');
      }
    }

    // Log mobile gain to verify it's not affected
    if (mobileGainNodeRef.current) {
      console.log('[AudioMixer] Mobile gain still at:', mobileGainNodeRef.current.gain.value);
    }

    // Log mixer state
    if (mixerDestinationRef.current) {
      console.log('[AudioMixer] Mixer still active, stream tracks:', mixerDestinationRef.current.stream.getTracks().length);
    }

    void recordEvent('controller', newMutedState ? 'desktop_microphone_muted' : 'desktop_microphone_unmuted', {
      hasMicrophone: desktopSourceRef.current?.hasMicrophone || false,
    });
  }, [recordEvent]);

  /**
   * Connect mobile audio source to mixer
   */
  const connectMobileAudio = useCallback((stream) => {
    if (!audioContextRef.current || !mobileGainNodeRef.current) {
      console.error('[AudioMixer] Cannot connect mobile audio - mixer not initialized');
      return;
    }

    const source = audioContextRef.current.createMediaStreamSource(stream);
    source.connect(mobileGainNodeRef.current);
    mobileAudioSourceRef.current = source;
    console.log('[AudioMixer] Mobile audio connected to mixer, tracks:', stream.getTracks().length);
  }, []);

  /**
   * Cleanup audio resources
   */
  const cleanup = useCallback(() => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    desktopSourceRef.current = null;
    mobileAudioSourceRef.current = null;
    mobileGainNodeRef.current = null;
    mixerDestinationRef.current = null;
  }, []);

  return {
    initializeMixer,
    toggleDesktopMute,
    connectMobileAudio,
    cleanup,
    // Refs for external access
    audioContextRef,
    micStreamRef,
    mixerDestinationRef,
    desktopGainNodeRef,
    mobileGainNodeRef,
  };
};

export default useAudioMixer;
