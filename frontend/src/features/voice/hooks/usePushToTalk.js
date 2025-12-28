import { useState, useRef, useCallback } from 'react';

/**
 * Hook for push-to-talk audio recording.
 * Records audio while button is pressed, returns base64 WAV.
 *
 * @param {Object} options
 * @param {Function} options.onRecordingComplete - Called with base64 WAV when recording stops
 * @param {Function} options.onError - Called with error if recording fails
 * @returns {Object} Recording state and control functions
 */
export default function usePushToTalk({ onRecordingComplete, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = useCallback(async () => {
    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 48000,
        }
      });
      streamRef.current = stream;

      // Determine supported MIME type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        try {
          const blob = new Blob(chunksRef.current, { type: mimeType });

          // Convert to WAV for OpenAI API
          const wavBlob = await convertToWav(blob);
          const base64 = await blobToBase64(wavBlob);

          onRecordingComplete?.(base64);
        } catch (err) {
          console.error('[usePushToTalk] Error processing audio:', err);
          onError?.(err);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.onerror = (e) => {
        console.error('[usePushToTalk] MediaRecorder error:', e);
        onError?.(new Error('Recording failed'));
        setIsRecording(false);
      };

      // Start recording - collect data every 100ms for smoother processing
      mediaRecorder.start(100);
      setIsRecording(true);
    } catch (err) {
      console.error('[usePushToTalk] Failed to start recording:', err);
      onError?.(err);
    }
  }, [onRecordingComplete, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }

    // Stop all tracks to release microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    setIsRecording(false);
  }, []);

  return {
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
    stream: streamRef.current
  };
}

/**
 * Convert blob to base64 string (without data URL prefix)
 */
async function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      // Remove "data:audio/wav;base64," prefix
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Convert audio blob to WAV format using AudioContext
 */
async function convertToWav(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();

  try {
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    // Convert to WAV
    const wavBuffer = audioBufferToWav(audioBuffer);
    return new Blob([wavBuffer], { type: 'audio/wav' });
  } finally {
    audioContext.close();
  }
}

/**
 * Convert AudioBuffer to WAV format ArrayBuffer
 */
function audioBufferToWav(buffer) {
  const numChannels = 1; // Mono for voice
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  // Get audio data (use first channel for mono)
  const inputData = buffer.getChannelData(0);

  // Resample to 24kHz if needed (OpenAI prefers 24kHz)
  const targetSampleRate = 24000;
  const data = sampleRate !== targetSampleRate
    ? resampleAudio(inputData, sampleRate, targetSampleRate)
    : inputData;

  const actualSampleRate = sampleRate !== targetSampleRate ? targetSampleRate : sampleRate;
  const dataLength = data.length * (bitDepth / 8);
  const bufferLength = 44 + dataLength;

  const arrayBuffer = new ArrayBuffer(bufferLength);
  const view = new DataView(arrayBuffer);

  // WAV header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, format, true); // audio format (PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, actualSampleRate, true);
  view.setUint32(28, actualSampleRate * numChannels * (bitDepth / 8), true); // byte rate
  view.setUint16(32, numChannels * (bitDepth / 8), true); // block align
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write audio data
  let offset = 44;
  for (let i = 0; i < data.length; i++) {
    const sample = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
    offset += 2;
  }

  return arrayBuffer;
}

/**
 * Simple linear interpolation resampling
 */
function resampleAudio(inputData, inputSampleRate, outputSampleRate) {
  const ratio = inputSampleRate / outputSampleRate;
  const outputLength = Math.floor(inputData.length / ratio);
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i * ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, inputData.length - 1);
    const frac = srcIndex - srcIndexFloor;

    // Linear interpolation
    output[i] = inputData[srcIndexFloor] * (1 - frac) + inputData[srcIndexCeil] * frac;
  }

  return output;
}

/**
 * Write string to DataView
 */
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
