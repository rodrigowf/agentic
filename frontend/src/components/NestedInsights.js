import React, { useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  Stack,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const safeStringify = (value) => {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
};

export default function NestedInsights({ nestedHighlights }) {
  const nestedScrollRef = useRef(null);

  useEffect(() => {
    const node = nestedScrollRef.current;
    if (node) {
      requestAnimationFrame(() => {
        node.scrollTop = node.scrollHeight;
      });
    }
  }, [nestedHighlights]);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <Typography variant="h6" sx={{ mb: 2, px: 3, pt: 3 }}>
        Nested Agent Insights
      </Typography>
      <Box
        ref={nestedScrollRef}
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          px: 3,
          pb: 3,
        }}
      >
        {nestedHighlights.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No nested activity captured yet.
          </Typography>
        ) : (
          <Stack spacing={1.25}>
            {nestedHighlights.map((entry) => {
              const chipColor = ['info', 'success', 'warning', 'error'].includes(entry.tone)
                ? entry.tone
                : 'default';
              return (
                <Accordion
                  key={entry.key}
                  disableGutters
                  elevation={0}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderLeft: '4px solid',
                    borderLeftColor: (theme) =>
                      chipColor === 'default'
                        ? theme.palette.divider
                        : theme.palette[chipColor].main,
                    bgcolor: 'background.paper',
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
                    <Stack spacing={0.5} sx={{ width: '100%' }}>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        <Chip
                          size="small"
                          label={entry.typeLabel}
                          color={chipColor === 'default' ? 'default' : chipColor}
                          variant={chipColor === 'default' ? 'outlined' : 'filled'}
                        />
                        <Chip size="small" label={entry.agentName} variant="outlined" />
                        {entry.role && <Chip size="small" label={entry.role} variant="outlined" />}
                        <Box sx={{ flexGrow: 1 }} />
                        {entry.timeLabel && (
                          <Typography variant="caption" color="text.secondary">
                            {entry.timeLabel}
                          </Typography>
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {entry.preview}
                      </Typography>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 2, pb: 2 }}>
                    <Stack spacing={1.25}>
                      {entry.detail && (
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {entry.detail}
                        </Typography>
                      )}
                      {(entry.metadata.length > 0 || entry.role) && (
                        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                          {entry.role && (
                            <Chip size="small" variant="outlined" label={`Role: ${entry.role}`} />
                          )}
                          {entry.metadata.map((meta, metaIdx) => (
                            <Chip
                              key={`${entry.key}-meta-${metaIdx}`}
                              size="small"
                              variant="outlined"
                              label={`${meta.label}: ${meta.value}`}
                            />
                          ))}
                        </Stack>
                      )}
                      <Divider />
                      <Box
                        component="pre"
                        sx={{
                          bgcolor: 'grey.900',
                          color: 'grey.100',
                          borderRadius: 1,
                          p: 1.25,
                          fontSize: 12,
                          overflowX: 'auto',
                          mb: 0,
                        }}
                      >
                        {safeStringify(entry.raw)}
                      </Box>
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Stack>
        )}
      </Box>
    </Box>
  );
}
