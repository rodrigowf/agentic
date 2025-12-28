import React, { useState, useRef, useCallback } from 'react';
import { Box, Alert } from '@mui/material';
import PushToTalkButton from './PushToTalkButton';
import usePushToTalk from '../hooks/usePushToTalk';
import { sendAudioMessage } from '../../../api';

/**
 * Controls for disconnected (non-WebRTC) voice mode.
 * Visible when WebRTC session is not active.
 *
 * Uses OpenAI Chat Completions API with gpt-4o-audio-preview
 * for audio input/output instead of realtime WebRTC.
 */
export default function DisconnectedVoiceControls({
  conversationId,
  voiceConfig,
  onError,
  onResponseAudio,
  onTranscript,
  onMessageSent,
  isSendingText  // External flag for text sending state
}) {
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);

  // Combined sending state (audio or text)
  const isAnySending = isSending || isSendingText;

  const handleRecordingComplete = useCallback(async (audioBase64) => {
    if (!conversationId) {
      setError('No conversation selected');
      return;
    }

    setIsSending(true);
    setError(null);

    try {
      // Send audio to backend
      const response = await sendAudioMessage(conversationId, {
        audio_base64: audioBase64,
        format: 'wav',
        voice: voiceConfig?.voice || 'cedar'
      });

      const { text, audio_base64: responseAudio, transcript } = response.data;

      console.log('[DisconnectedVoice] Response received:', {
        text: text || '(empty)',
        textLength: text?.length || 0,
        hasAudio: !!responseAudio,
        audioLength: responseAudio?.length || 0,
        transcript: transcript || '(no transcript)'
      });

      // Notify parent of transcript if provided
      if (transcript) {
        onTranscript?.(transcript);
      }

      // Play response audio if available
      if (responseAudio && audioRef.current) {
        const audioData = `data:audio/wav;base64,${responseAudio}`;
        audioRef.current.src = audioData;

        try {
          await audioRef.current.play();
        } catch (playError) {
          console.warn('[DisconnectedVoice] Audio playback failed:', playError);
        }
      }

      onResponseAudio?.(responseAudio, text);
      onMessageSent?.();

    } catch (err) {
      console.error('[DisconnectedVoice] Failed to send audio:', err);
      const detail = err?.response?.data?.detail || err.message || 'Failed to send audio';
      setError(detail);
      onError?.(err);
    } finally {
      setIsSending(false);
    }
  }, [conversationId, voiceConfig, onResponseAudio, onTranscript, onError, onMessageSent]);

  const handleError = useCallback((err) => {
    console.error('[DisconnectedVoice] Recording error:', err);
    setError(err.message || 'Recording failed');
    onError?.(err);
  }, [onError]);

  const {
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
    stream
  } = usePushToTalk({
    onRecordingComplete: handleRecordingComplete,
    onError: handleError
  });

  const handleDismissError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <Box>
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={handleDismissError}
        >
          {error}
        </Alert>
      )}

      <PushToTalkButton
        isRecording={isRecording}
        isProcessing={isProcessing}
        isSending={isAnySending}
        onPressStart={startRecording}
        onPressEnd={stopRecording}
        disabled={!conversationId}
        stream={stream}
      />

      {/* Hidden audio element for playback */}
      <audio
        ref={audioRef}
        style={{ display: 'none' }}
        onEnded={() => console.log('[DisconnectedVoice] Audio playback ended')}
        onError={(e) => console.warn('[DisconnectedVoice] Audio element error:', e)}
      />
    </Box>
  );
}
