import React, { useState } from 'react';
import {
  Button,
  IconButton,
  Tooltip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
  Box,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PublishIcon from '@mui/icons-material/Publish';
import { refreshService, pushChanges } from '../../api';

export default function ServerManagementButtons({ iconOnly = false }) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [refreshDialog, setRefreshDialog] = useState({ open: false, result: null });
  const [pushDialog, setPushDialog] = useState({ open: false, result: null });

  const handleRefreshService = async () => {
    setIsRefreshing(true);
    try {
      const response = await refreshService();
      const result = response.data;

      setRefreshDialog({ open: true, result });

      if (result.success) {
        // Wait 3 seconds then reload the page to see the changes
        setTimeout(() => {
          window.location.reload();
        }, 3000);
      }
    } catch (error) {
      setRefreshDialog({
        open: true,
        result: {
          success: false,
          error: error.response?.data?.error || error.message || 'Unknown error',
        },
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handlePushChanges = async () => {
    setIsPushing(true);
    try {
      const response = await pushChanges();
      const result = response.data;

      setPushDialog({ open: true, result });
    } catch (error) {
      setPushDialog({
        open: true,
        result: {
          success: false,
          error: error.response?.data?.error || error.message || 'Unknown error',
        },
      });
    } finally {
      setIsPushing(false);
    }
  };

  const handleCloseRefreshDialog = () => {
    setRefreshDialog({ open: false, result: null });
  };

  const handleClosePushDialog = () => {
    setPushDialog({ open: false, result: null });
  };

  if (iconOnly) {
    return (
      <>
        <Tooltip title="Push local changes to git" arrow>
          <IconButton
            onClick={handlePushChanges}
            disabled={isPushing}
            color="inherit"
            aria-label="Push local changes"
          >
            {isPushing ? <CircularProgress size={24} color="inherit" /> : <PublishIcon />}
          </IconButton>
        </Tooltip>
        <Tooltip title="Refresh service (pull + build + restart)" arrow>
          <IconButton
            onClick={handleRefreshService}
            disabled={isRefreshing}
            color="inherit"
            aria-label="Refresh service"
          >
            {isRefreshing ? <CircularProgress size={24} color="inherit" /> : <RefreshIcon />}
          </IconButton>
        </Tooltip>

        {/* Dialogs */}
        <RefreshDialog
          open={refreshDialog.open}
          result={refreshDialog.result}
          onClose={handleCloseRefreshDialog}
        />
        <PushDialog
          open={pushDialog.open}
          result={pushDialog.result}
          onClose={handleClosePushDialog}
        />
      </>
    );
  }

  return (
    <>
      <Button
        onClick={handlePushChanges}
        disabled={isPushing}
        startIcon={isPushing ? <CircularProgress size={20} /> : <PublishIcon />}
        color="inherit"
      >
        Push Changes
      </Button>
      <Button
        onClick={handleRefreshService}
        disabled={isRefreshing}
        startIcon={isRefreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
        color="inherit"
      >
        Refresh Service
      </Button>

      {/* Dialogs */}
      <RefreshDialog
        open={refreshDialog.open}
        result={refreshDialog.result}
        onClose={handleCloseRefreshDialog}
      />
      <PushDialog
        open={pushDialog.open}
        result={pushDialog.result}
        onClose={handleClosePushDialog}
      />
    </>
  );
}

function RefreshDialog({ open, result, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {result?.success ? 'Service Refresh Successful' : 'Service Refresh Failed'}
      </DialogTitle>
      <DialogContent>
        {result && (
          <Box>
            {result.success ? (
              <>
                <Alert severity="success" sx={{ mb: 2 }}>
                  {result.message}
                </Alert>
                <DialogContentText sx={{ mb: 1 }}>
                  <strong>Git Output:</strong>
                </DialogContentText>
                <DialogContentText
                  component="pre"
                  sx={{
                    fontSize: '0.75rem',
                    backgroundColor: 'background.subtile',
                    p: 1,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 200,
                    mb: 2,
                  }}
                >
                  {result.git_output || 'Already up to date.'}
                </DialogContentText>
                <DialogContentText sx={{ mb: 1 }}>
                  <strong>Build Output:</strong>
                </DialogContentText>
                <DialogContentText
                  component="pre"
                  sx={{
                    fontSize: '0.75rem',
                    backgroundColor: 'background.subtile',
                    p: 1,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 200,
                  }}
                >
                  {result.build_output || 'Build completed.'}
                </DialogContentText>
                <Alert severity="info" sx={{ mt: 2 }}>
                  Page will reload in 3 seconds to show the changes...
                </Alert>
              </>
            ) : (
              <>
                <Alert severity="error" sx={{ mb: 2 }}>
                  {result.error || 'Unknown error occurred'}
                </Alert>
                {result.step && (
                  <DialogContentText>
                    Failed at step: <strong>{result.step}</strong>
                  </DialogContentText>
                )}
              </>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

function PushDialog({ open, result, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {result?.success ? 'Push Successful' : 'Push Failed'}
      </DialogTitle>
      <DialogContent>
        {result && (
          <Box>
            {result.success ? (
              <>
                <Alert severity="success" sx={{ mb: 2 }}>
                  {result.message}
                </Alert>
                {result.pushed && (
                  <>
                    <DialogContentText sx={{ mb: 1 }}>
                      <strong>Commit Message:</strong>
                    </DialogContentText>
                    <DialogContentText
                      sx={{
                        fontSize: '0.875rem',
                        backgroundColor: 'background.subtile',
                        p: 1,
                        borderRadius: 1,
                        mb: 2,
                      }}
                    >
                      {result.commit_message}
                    </DialogContentText>
                    <DialogContentText sx={{ mb: 1 }}>
                      <strong>Push Output:</strong>
                    </DialogContentText>
                    <DialogContentText
                      component="pre"
                      sx={{
                        fontSize: '0.75rem',
                        backgroundColor: 'background.subtile',
                        p: 1,
                        borderRadius: 1,
                        overflow: 'auto',
                        maxHeight: 200,
                      }}
                    >
                      {result.push_output || 'Pushed successfully.'}
                    </DialogContentText>
                  </>
                )}
              </>
            ) : (
              <>
                <Alert severity="error" sx={{ mb: 2 }}>
                  {result.error || 'Unknown error occurred'}
                </Alert>
                {result.step && (
                  <DialogContentText>
                    Failed at step: <strong>{result.step}</strong>
                  </DialogContentText>
                )}
              </>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
