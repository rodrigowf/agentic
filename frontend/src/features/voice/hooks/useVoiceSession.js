import { useState, useRef, useCallback } from 'react';

/**
 * Core session state management for voice assistant
 * Manages session lifecycle, mute states, errors, and configuration
 */
export const useVoiceSession = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  const [noMicrophoneMode, setNoMicrophoneMode] = useState(false);
  const [voiceConfig, setVoiceConfig] = useState({
    agentName: 'MainConversation',
    systemPromptFile: 'default.txt',
    systemPromptContent: '',
    voice: 'alloy',
  });

  // Refs for tracking tool calls and run state
  const toolCallsRef = useRef({});
  const lastVoiceToolCallRef = useRef({ name: null, timestamp: 0 });
  const hasSpokenMidRef = useRef(false);
  const runCompletedRef = useRef(false);

  const resetSessionState = useCallback(() => {
    setIsRunning(false);
    setIsMuted(false);
    setIsSpeakerMuted(false);
    setNoMicrophoneMode(false);
    setError(null);
    hasSpokenMidRef.current = false;
    runCompletedRef.current = false;
    toolCallsRef.current = {};
  }, []);

  return {
    // State
    isRunning,
    setIsRunning,
    isMuted,
    setIsMuted,
    isSpeakerMuted,
    setIsSpeakerMuted,
    transcript,
    setTranscript,
    error,
    setError,
    noMicrophoneMode,
    setNoMicrophoneMode,
    voiceConfig,
    setVoiceConfig,

    // Refs
    toolCallsRef,
    lastVoiceToolCallRef,
    hasSpokenMidRef,
    runCompletedRef,

    // Methods
    resetSessionState,
  };
};

export default useVoiceSession;
