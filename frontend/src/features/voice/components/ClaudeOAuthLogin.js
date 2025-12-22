/**
 * ClaudeOAuthLogin - OAuth login component for Claude Code
 *
 * Provides two authentication options:
 * 1. OAuth via Claude.ai (for Claude.ai subscribers)
 * 2. API Key (for Anthropic API users)
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Button,
  TextField,
  Paper,
  Divider,
  Alert,
  CircularProgress,
  Link,
  Collapse,
  alpha,
} from '@mui/material';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import KeyIcon from '@mui/icons-material/Key';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  getClaudeAuthStatus,
  setClaudeApiKey,
  startClaudeOAuth,
  sendClaudeOAuthInput,
  cancelClaudeOAuth,
  getClaudeOAuthEventsUrl,
} from '../../../api';

const ClaudeOAuthLogin = ({ onAuthenticated, compact = false }) => {
  const [authStatus, setAuthStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState(null);

  // OAuth state
  const [oauthStatus, setOauthStatus] = useState('idle');
  const [authUrl, setAuthUrl] = useState(null);
  const [authCode, setAuthCode] = useState('');
  const [isSubmittingCode, setIsSubmittingCode] = useState(false);
  const eventSourceRef = useRef(null);

  // API Key state
  const [showApiKeyForm, setShowApiKeyForm] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [isSubmittingKey, setIsSubmittingKey] = useState(false);

  // Check authentication status
  const checkAuth = useCallback(async () => {
    setIsChecking(true);
    setError(null);
    try {
      const res = await getClaudeAuthStatus();
      setAuthStatus(res.data);
      if (res.data?.isAuthenticated && onAuthenticated) {
        onAuthenticated(res.data);
      }
    } catch (err) {
      setError('Failed to check authentication status');
      console.error('[ClaudeOAuth] Error checking auth:', err);
    } finally {
      setIsChecking(false);
    }
  }, [onAuthenticated]);

  useEffect(() => {
    checkAuth();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [checkAuth]);

  // Subscribe to OAuth events via SSE
  const subscribeToOAuthEvents = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventsUrl = getClaudeOAuthEventsUrl();
    const eventSource = new EventSource(eventsUrl);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const status = JSON.parse(event.data);
        console.log('[ClaudeOAuth] SSE status:', status);
        handleOAuthStatusUpdate(status);
      } catch (err) {
        console.error('[ClaudeOAuth] Error parsing SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('[ClaudeOAuth] SSE error:', err);
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, []);

  const handleOAuthStatusUpdate = (status) => {
    setOauthStatus(status.status);

    switch (status.status) {
      case 'waiting_for_url':
        setError(null);
        break;
      case 'url_ready':
        setAuthUrl(status.authUrl);
        setError(null);
        break;
      case 'authenticating':
        setIsSubmittingCode(true);
        break;
      case 'success':
        setIsSubmittingCode(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        checkAuth();
        break;
      case 'error':
        setIsSubmittingCode(false);
        setError(status.error || 'Authentication failed');
        setOauthStatus('idle');
        break;
      default:
        break;
    }
  };

  // Start OAuth flow
  const handleStartOAuth = async () => {
    setError(null);
    setAuthUrl(null);
    setAuthCode('');
    setOauthStatus('starting');

    try {
      await startClaudeOAuth();
      subscribeToOAuthEvents();
    } catch (err) {
      setError('Failed to start OAuth flow');
      setOauthStatus('idle');
      console.error('[ClaudeOAuth] Error starting OAuth:', err);
    }
  };

  // Submit authorization code
  const handleSubmitCode = async () => {
    if (!authCode.trim()) return;
    setIsSubmittingCode(true);
    setError(null);

    try {
      await sendClaudeOAuthInput(authCode.trim());
    } catch (err) {
      setError('Failed to submit authorization code');
      setIsSubmittingCode(false);
      console.error('[ClaudeOAuth] Error submitting code:', err);
    }
  };

  // Cancel OAuth flow
  const handleCancelOAuth = async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    try {
      await cancelClaudeOAuth();
    } catch (err) {
      console.error('[ClaudeOAuth] Error canceling OAuth:', err);
    }
    setOauthStatus('idle');
    setAuthUrl(null);
    setAuthCode('');
  };

  // Submit API key
  const handleSubmitApiKey = async () => {
    if (!apiKey.trim()) return;
    setIsSubmittingKey(true);
    setError(null);

    try {
      await setClaudeApiKey(apiKey.trim());
      setApiKey('');
      setShowApiKeyForm(false);
      await checkAuth();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to set API key');
      console.error('[ClaudeOAuth] Error setting API key:', err);
    } finally {
      setIsSubmittingKey(false);
    }
  };

  // Loading state
  if (isChecking) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', p: 3 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Checking authentication...
        </Typography>
      </Box>
    );
  }

  // Already authenticated
  if (authStatus?.isAuthenticated) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: compact ? 1 : 2 }}>
        <CheckCircleIcon color="success" fontSize="small" />
        <Typography variant="body2" color="text.secondary">
          Claude Code ready
          {authStatus.method === 'oauth' && ' (OAuth)'}
          {authStatus.method === 'api_key' && ' (API Key)'}
        </Typography>
      </Box>
    );
  }

  // Show login form
  return (
    <Paper
      variant="outlined"
      sx={{
        p: compact ? 2 : 3,
        maxWidth: 480,
        mx: 'auto',
        bgcolor: (theme) => alpha(theme.palette.background.paper, 0.8),
      }}
    >
      <Typography variant="h6" gutterBottom>
        Claude Code Authentication
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Authenticate to enable Claude Code features. Choose one of the options below.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* OAuth Flow */}
      {oauthStatus === 'idle' || oauthStatus === 'starting' ? (
        <Button
          variant="contained"
          fullWidth
          startIcon={<LockOpenIcon />}
          onClick={handleStartOAuth}
          disabled={oauthStatus === 'starting'}
          sx={{ mb: 2 }}
        >
          {oauthStatus === 'starting' ? (
            <>
              <CircularProgress size={16} sx={{ mr: 1 }} />
              Starting...
            </>
          ) : (
            'Log in with Claude.ai'
          )}
        </Button>
      ) : (
        <Box sx={{ mb: 2 }}>
          {oauthStatus === 'waiting_for_url' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={16} />
              <Typography variant="body2">Waiting for authentication URL...</Typography>
            </Box>
          )}

          {(oauthStatus === 'url_ready' || authUrl) && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                1. Click the link below to authenticate:
              </Typography>
              <Link
                href={authUrl}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  mb: 2,
                  fontSize: '0.875rem',
                  wordBreak: 'break-all',
                }}
              >
                Open Claude.ai
                <OpenInNewIcon fontSize="inherit" />
              </Link>

              <Typography variant="body2" sx={{ mb: 1 }}>
                2. After authenticating, paste the code below:
              </Typography>
              <TextField
                fullWidth
                size="small"
                placeholder="Paste authorization code here"
                value={authCode}
                onChange={(e) => setAuthCode(e.target.value)}
                disabled={isSubmittingCode}
                sx={{ mb: 1 }}
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  onClick={handleSubmitCode}
                  disabled={!authCode.trim() || isSubmittingCode}
                  sx={{ flex: 1 }}
                >
                  {isSubmittingCode ? (
                    <>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      Verifying...
                    </>
                  ) : (
                    'Submit Code'
                  )}
                </Button>
                <Button
                  variant="outlined"
                  onClick={handleCancelOAuth}
                  disabled={isSubmittingCode}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      )}

      <Divider sx={{ my: 2 }}>
        <Typography variant="caption" color="text.secondary">
          OR
        </Typography>
      </Divider>

      {/* API Key Form */}
      <Button
        variant="outlined"
        fullWidth
        startIcon={<KeyIcon />}
        onClick={() => setShowApiKeyForm(!showApiKeyForm)}
        disabled={oauthStatus !== 'idle'}
      >
        Use API Key
      </Button>

      <Collapse in={showApiKeyForm}>
        <Box sx={{ mt: 2 }}>
          <TextField
            fullWidth
            size="small"
            type="password"
            label="Anthropic API Key"
            placeholder="sk-ant-api..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={isSubmittingKey}
            sx={{ mb: 1 }}
          />
          <Button
            variant="contained"
            fullWidth
            onClick={handleSubmitApiKey}
            disabled={!apiKey.trim() || isSubmittingKey}
          >
            {isSubmittingKey ? (
              <>
                <CircularProgress size={16} sx={{ mr: 1 }} />
                Saving...
              </>
            ) : (
              'Save API Key'
            )}
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Get your API key from{' '}
            <Link href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">
              console.anthropic.com
            </Link>
          </Typography>
        </Box>
      </Collapse>
    </Paper>
  );
};

ClaudeOAuthLogin.propTypes = {
  onAuthenticated: PropTypes.func,
  compact: PropTypes.bool,
};

export default ClaudeOAuthLogin;
