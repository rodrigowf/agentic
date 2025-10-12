import React, { useEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { AudioVisualizerProps } from '../../../types';

/**
 * AudioVisualizer - A modern, elegant audio activity visualizer
 * Displays animated bars that respond to microphone input volume
 */
export default function AudioVisualizer({
  stream,
  isActive = true,
  isMuted = false
}: AudioVisualizerProps & { stream?: MediaStream | null }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const [volume, setVolume] = useState<number>(0);

  useEffect(() => {
    if (!stream || !isActive || isMuted) {
      // Clean up analyzer when inactive or muted
      if (audioContextRef.current) {
        try {
          // Only close if not already closed
          if (audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close().catch((err: Error) => {
              // Silently log to console, don't throw
              console.debug('AudioContext close warning:', err.message);
            });
          }
        } catch (e) {
          // Silently log to console, don't throw
          const error = e as Error;
          console.debug('AudioContext cleanup warning:', error.message);
        }
        audioContextRef.current = null;
      }
      analyserRef.current = null;
      dataArrayRef.current = null;

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      setVolume(0);
      return;
    }

    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      dataArrayRef.current = dataArray;

      const updateVolume = (): void => {
        if (!analyserRef.current || !dataArrayRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArrayRef.current);

        // Calculate average volume
        const sum = dataArrayRef.current.reduce((acc: number, val: number) => acc + val, 0);
        const avg = sum / dataArrayRef.current.length;
        const normalized = Math.min(avg / 128, 1); // Normalize to 0-1

        setVolume(normalized);
        animationRef.current = requestAnimationFrame(updateVolume);
      };

      updateVolume();

      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
        if (audioContextRef.current) {
          try {
            // Only close if not already closed
            if (audioContextRef.current.state !== 'closed') {
              audioContextRef.current.close().catch((err: Error) => {
                // Silently log to console, don't throw
                console.debug('AudioContext cleanup on unmount:', err.message);
              });
            }
          } catch (e) {
            // Silently log to console, don't throw
            const error = e as Error;
            console.debug('AudioContext cleanup warning on unmount:', error.message);
          }
        }
      };
    } catch (error) {
      console.error('Error setting up audio visualizer:', error);
    }
  }, [stream, isActive, isMuted]);

  // Render visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    if (!isActive || isMuted) {
      // Draw inactive state - flat lines
      ctx.fillStyle = 'rgba(100, 100, 100, 0.2)';
      for (let i = 0; i < 5; i++) {
        const x = (width / 6) * (i + 1);
        const barHeight = 4;
        const y = height / 2 - barHeight / 2;
        ctx.fillRect(x - 2, y, 4, barHeight);
      }
      return;
    }

    // Active state - animated bars
    const barCount = 5;
    const barWidth = 4;
    const spacing = width / (barCount + 1);

    for (let i = 0; i < barCount; i++) {
      const x = spacing * (i + 1);

      // Create wave effect with offset
      const offset = (i - barCount / 2) * 0.3;
      const amplitude = volume * 0.7 + Math.sin(Date.now() / 200 + offset) * 0.15;
      const barHeight = Math.max(4, height * amplitude * 0.8);

      const y = height / 2 - barHeight / 2;

      // Gradient based on volume
      const gradient = ctx.createLinearGradient(x, y, x, y + barHeight);
      if (volume > 0.6) {
        gradient.addColorStop(0, 'rgba(76, 175, 80, 0.9)');  // Green
        gradient.addColorStop(1, 'rgba(139, 195, 74, 0.6)');
      } else if (volume > 0.3) {
        gradient.addColorStop(0, 'rgba(33, 150, 243, 0.9)');  // Blue
        gradient.addColorStop(1, 'rgba(100, 181, 246, 0.6)');
      } else {
        gradient.addColorStop(0, 'rgba(158, 158, 158, 0.7)');  // Gray
        gradient.addColorStop(1, 'rgba(189, 189, 189, 0.4)');
      }

      ctx.fillStyle = gradient;
      ctx.fillRect(x - barWidth / 2, y, barWidth, barHeight);

      // Add glow effect for high volume
      if (volume > 0.5) {
        ctx.shadowBlur = 10;
        ctx.shadowColor = volume > 0.6 ? 'rgba(76, 175, 80, 0.5)' : 'rgba(33, 150, 243, 0.5)';
        ctx.fillRect(x - barWidth / 2, y, barWidth, barHeight);
        ctx.shadowBlur = 0;
      }
    }
  }, [volume, isActive, isMuted]);

  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        minWidth: '120px',
        height: '40px',
        borderRadius: '20px',
        bgcolor: (theme) => {
          if (!isActive || isMuted) {
            return theme.palette.mode === 'dark'
              ? 'rgba(255, 255, 255, 0.05)'
              : 'rgba(0, 0, 0, 0.04)';
          }
          // Active state - soft primary color background
          return theme.palette.mode === 'dark'
            ? 'rgba(33, 150, 243, 0.15)'  // Soft blue
            : 'rgba(25, 118, 210, 0.08)';  // Softer blue for light mode
        },
        boxShadow: isActive && !isMuted
          ? '0 2px 8px rgba(33, 150, 243, 0.15)'
          : 'none',
        transition: 'all 0.3s ease',
        px: 2,
      }}
    >
      <canvas
        ref={canvasRef}
        width={100}
        height={32}
        style={{
          width: '100px',
          height: '32px',
        }}
      />
    </Box>
  );
}
