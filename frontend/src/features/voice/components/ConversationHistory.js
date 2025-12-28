import React, { useMemo, useState, useRef, useEffect } from 'react';
import { Virtuoso } from 'react-virtuoso';
import {
	Box,
	Stack,
	Typography,
	Chip,
	Paper,
	Accordion,
	AccordionSummary,
	AccordionDetails,
	Divider,
	CircularProgress,
	Alert,
	Button,
	Collapse,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GraphicEqIcon from '@mui/icons-material/GraphicEq';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import CodeIcon from '@mui/icons-material/Code';
import HubIcon from '@mui/icons-material/Hub';
import TimelineIcon from '@mui/icons-material/Timeline';

const fallbackFormatTimestamp = (value) => {
	if (!value) return '';
	try {
		return new Date(value).toLocaleString();
	} catch (e) {
		return String(value);
	}
};

const truncateText = (value, max = 140) => {
	if (!value) return '';
	const str = String(value).trim();
	if (str.length <= max) return str;
	return `${str.slice(0, max - 1)}…`;
};

const formatDurationMs = (start, end) => {
	if (typeof start !== 'number' || typeof end !== 'number') return null;
	const diff = Math.max(0, end - start);
	if (!Number.isFinite(diff)) return null;
	if (diff < 1000) return `${diff} ms`;
	if (diff < 10000) return `${(diff / 1000).toFixed(1)} s`;
	return `${Math.round(diff / 1000)} s`;
};

const safeStringify = (value) => {
	if (value == null) return '';
	if (typeof value === 'string') return value;
	try {
		return JSON.stringify(value, null, 2);
	} catch (e) {
		return String(value);
	}
};

const summarizeEvent = (msg) => {
	if (!msg) return '';
	const typeLower = (msg.type || '').toLowerCase();
	const data = msg.data || {};
	switch (typeLower) {
		case 'response.created': {
			const parts = [];
			if (data.response?.id) parts.push(`id ${data.response.id}`);
			if (data.response?.voice) parts.push(`voice ${data.response.voice}`);
			if (Array.isArray(data.response?.modalities) && data.response.modalities.length) {
				parts.push(`modalities ${data.response.modalities.join('/')}`);
			}
			return parts.length ? `Response created (${parts.join(' · ')})` : 'Response created';
		}
		case 'response.done': {
			const status = data.response?.status || data.response?.status_details?.reason;
			const tokens = data.response?.usage?.total_tokens;
			const details = [];
			if (status) details.push(status);
			if (typeof tokens === 'number') details.push(`${tokens} tokens`);
			return details.length ? `Response finished (${details.join(' · ')})` : 'Response finished';
		}
		case 'response.output_item.added': {
			const item = data.item;
			if (!item) return 'Output item added';
			const label = [item.type, item.role].filter(Boolean).join(' · ');
			return label ? `Output item added (${label})` : 'Output item added';
		}
		case 'response.output_item.done': {
			const item = data.item;
			if (!item) return 'Output item completed';
			const transcript = item.content?.find((c) => c?.type === 'audio')?.transcript;
			return transcript ? `Output item completed: ${truncateText(transcript, 120)}` : 'Output item completed';
		}
		case 'response.content_part.added': {
			const partType = data.part?.type || 'part';
			return `Content part added (${partType})`;
		}
		case 'response.content_part.done': {
			const partType = data.part?.type || 'part';
			return `Content part completed (${partType})`;
		}
		case 'response.audio_transcript.delta':
			return data.delta ? `Audio chunk: ${truncateText(data.delta, 60)}` : 'Audio chunk';
		case 'response.audio_transcript.done':
			return data.transcript ? `Transcript ready: ${truncateText(data.transcript, 120)}` : 'Transcript ready';
		case 'response.audio.done':
			return 'Audio stream completed';
		case 'input_audio_buffer.speech_started':
			return typeof data.audio_start_ms === 'number' ? `Speech started at ${(data.audio_start_ms / 1000).toFixed(2)} s` : 'Speech started';
		case 'input_audio_buffer.speech_stopped':
			return typeof data.audio_end_ms === 'number' ? `Speech stopped at ${(data.audio_end_ms / 1000).toFixed(2)} s` : 'Speech stopped';
		case 'input_audio_buffer.committed':
			return 'Input audio committed';
		case 'response.function_call_arguments.delta':
			return data.delta ? `Args chunk: ${truncateText(data.delta, 80)}` : 'Args chunk';
		case 'response.function_call_arguments.done':
			return 'Arguments streaming finished';
		case 'response.function_call_arguments.created':
			return 'Function call arguments started';
		case 'response.function_call.completed':
			return 'Function call completed';
		case 'response.function_call':
			return data.name ? `Function call ${data.name}` : 'Function call';
		case 'controller.voice_forward':
			return data.text ? `Forwarded to voice: ${truncateText(data.text, 120)}` : 'Forwarded message to voice channel';
		case 'controller.tool_exec':
			return data.tool ? `Tool executed: ${data.tool}` : 'Tool executed';
		case 'controller.session_started':
			return 'Session started';
		case 'controller.session_stopped':
			return 'Session stopped';
		case 'controller.session_error':
			return data.message ? `Session error: ${truncateText(data.message, 120)}` : 'Session error';
		case 'controller.system':
			return data.message ? truncateText(data.message, 140) : 'Controller system message';
		case 'controller.error':
			return data.message ? `Controller error: ${truncateText(data.message, 120)}` : 'Controller error';
		case 'controller.history_replay':
			return data.count ? `Replayed ${data.count} item(s)` : 'History replay';
		case 'nested.textmessage': {
			const content = data.data?.content || data.data?.message;
			const speaker = data.data?.source || 'Nested agent';
			return content ? `${speaker}: ${truncateText(content, 160)}` : `${speaker} text message`;
		}
		case 'nested.system':
			return data.message ? truncateText(data.message, 160) : 'Nested system message';
		case 'nested.toolcallrequestevent':
			return data.data?.name ? `Tool requested: ${data.data.name}` : 'Tool request event';
		case 'nested.toolcallexecutionevent':
			return data.data?.result ? `Tool completed: ${truncateText(data.data.result, 140)}` : 'Tool execution event';
		case 'nested.error':
			return data.message ? `Nested error: ${truncateText(data.message, 160)}` : 'Nested error';
		case 'voice.parse_error':
		case 'nested.parse_error':
			return 'Parse error';
		case 'rate_limits.updated':
			if (Array.isArray(data.rate_limits) && data.rate_limits.length) {
				const rate = data.rate_limits[0];
				if (rate.remaining != null) return `Rate limits: ${rate.remaining} remaining`;
			}
			return 'Rate limits updated';
		// Disconnected voice mode events
		case 'disconnected_user_audio':
			return data.transcript ? `You (audio): ${truncateText(data.transcript, 120)}` : 'Audio message sent';
		case 'disconnected_user_text':
			return data.text ? `You: ${truncateText(data.text, 120)}` : 'Text message sent';
		case 'disconnected_assistant_response':
			return data.text ? `Assistant: ${truncateText(data.text, 120)}` : 'Assistant response';
		case 'disconnected_tool_call':
			const toolName = data.tool || 'unknown';
			const success = data.result?.success ? '✓' : '✗';
			return `Tool ${success}: ${toolName}`;
		default:
			return '';
	}
};

const buildTimeSubtitle = (first, last, formatTimestamp) => {
	if (!first && !last) return '';
	if (first && last && first !== last) {
		return `${formatTimestamp(first)} → ${formatTimestamp(last)}`;
	}
	return formatTimestamp(first || last);
};

const groupIconKind = (kind) => {
	switch (kind) {
		case 'assistant-response':
			return GraphicEqIcon;
		case 'user-speech':
			return PersonOutlineIcon;
		case 'tool-call':
			return CodeIcon;
		case 'controller-forward':
			return HubIcon;
		default:
			return TimelineIcon;
	}
};

const HistoryEventRow = ({ event, formatTimestamp }) => {
	const { msg, summary } = event;
	const [open, setOpen] = useState(false);
	const timeLabel = formatTimestamp(msg.timestamp);
	return (
		<Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1.25 }}>
			<Stack direction="row" spacing={1} alignItems="center" sx={{ mb: summary ? 0.5 : 0, flexWrap: 'wrap' }}>
				<Chip size="small" label={msg.type || 'event'} variant="outlined" />
				{msg.source && (
					<Chip size="small" label={msg.source} variant="outlined" color={msg.source === 'nested' ? 'secondary' : 'default'} />
				)}
				{timeLabel && (
					<Typography variant="caption" color="text.secondary">{timeLabel}</Typography>
				)}
				<Box sx={{ flexGrow: 1 }} />
				<Button size="small" onClick={() => setOpen((prev) => !prev)}>
					{open ? 'Hide raw' : 'Show raw'}
				</Button>
			</Stack>
			{summary && (
				<Typography variant="body2" color="text.secondary">{summary}</Typography>
			)}
			<Collapse in={open} timeout="auto" unmountOnExit>
				<Box
					component="pre"
					sx={{
						mt: 1,
						bgcolor: 'grey.600',
						color: 'grey.100',
						borderRadius: 1,
						p: 1,
						fontSize: 12,
						overflowX: 'auto',
					}}
				>
					{safeStringify(msg.data ?? msg)}
				</Box>
			</Collapse>
		</Box>
	);
};

const HistoryDeltaGroup = ({ entry }) => {
	const [open, setOpen] = useState(false);
	const [showChunks, setShowChunks] = useState(false);
	const preview = truncateText(entry.text || '', 160) || 'Audio transcript stream';
	return (
		<Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1.25 }}>
			<Stack direction="row" spacing={1} alignItems="center">
				<Chip size="small" icon={<GraphicEqIcon fontSize="small" />} label={`Audio transcript (${entry.count} chunk${entry.count === 1 ? '' : 's'})`} />
				<Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>{preview}</Typography>
				<Stack direction="row" spacing={1}>
					{entry.text && (
						<Button size="small" onClick={() => setOpen((prev) => !prev)}>
							{open ? 'Hide transcript' : 'View transcript'}
						</Button>
					)}
					<Button size="small" onClick={() => setShowChunks((prev) => !prev)}>
						{showChunks ? 'Hide events' : 'Show events'}
					</Button>
				</Stack>
			</Stack>
			<Collapse in={open} timeout="auto" unmountOnExit>
				<Typography variant="body2" sx={{ mt: 1 }}>{entry.text}</Typography>
			</Collapse>
			<Collapse in={showChunks} timeout="auto" unmountOnExit>
				<Stack spacing={1} sx={{ mt: 1 }}>
					{entry.events.map((chunk, idx) => (
						<Box key={chunk.id ?? idx} component="pre" sx={{ bgcolor: 'grey.900', color: 'grey.100', borderRadius: 1, p: 1, fontSize: 12, overflowX: 'auto' }}>
							{safeStringify(chunk.data ?? chunk)}
						</Box>
					))}
				</Stack>
			</Collapse>
		</Box>
	);
};

const buildGroupedHistory = (messages, formatTimestamp) => {
	if (!messages || messages.length === 0) return [];

	const itemToResponse = new Map();

	messages.forEach((msg) => {
		if (!msg) return;
		const typeLower = (msg.type || '').toLowerCase();
		const data = msg.data || {};
		if (typeLower === 'response.output_item.added' && data.item?.id && data.response_id) {
			itemToResponse.set(data.item.id, data.response_id);
		}
		if (typeLower === 'response.output_item.done' && data.item?.id && data.response_id) {
			itemToResponse.set(data.item.id, data.response_id);
		}
	});

	const groupsMap = new Map();
	const groupsList = [];

	const ensureGroup = (key, defaults) => {
		let group = groupsMap.get(key);
		if (!group) {
			group = {
				key,
				events: [],
				badges: [],
				timeline: [],
				summaryFormat: 'text',
				firstTimestamp: null,
				lastTimestamp: null,
				...defaults,
			};
			groupsMap.set(key, group);
			groupsList.push(group);
		}
		return group;
	};

	messages.forEach((msg, index) => {
		if (!msg) return;
		const data = msg.data || {};
		const typeLower = (msg.type || '').toLowerCase();
		const sourceLower = (msg.source || '').toLowerCase();

		const responseId = data.response_id
			|| data.response?.id
			|| (data.item_id && itemToResponse.get(data.item_id))
			|| (data.item?.id && itemToResponse.get(data.item.id));

		let groupKey;
		let defaults;

		// Handle disconnected voice mode events with their own groups
		if (typeLower === 'disconnected_user_audio') {
			groupKey = `disconnected-user:${msg.id || `audio-${index}`}`;
			defaults = { kind: 'user-speech', label: 'User (audio)', source: 'disconnected' };
		} else if (typeLower === 'disconnected_user_text') {
			groupKey = `disconnected-user:${msg.id || `text-${index}`}`;
			defaults = { kind: 'user-speech', label: 'User (text)', source: 'disconnected' };
		} else if (typeLower === 'disconnected_assistant_response') {
			groupKey = `disconnected-assistant:${msg.id || `response-${index}`}`;
			defaults = { kind: 'assistant-response', label: 'Assistant (disconnected)', source: 'disconnected' };
		} else if (typeLower === 'disconnected_tool_call') {
			groupKey = `disconnected-tool:${msg.id || `tool-${index}`}`;
			defaults = { kind: 'tool-call', label: 'Tool call (disconnected)', source: 'disconnected' };
		} else if (responseId) {
			groupKey = `response:${responseId}`;
			defaults = { kind: 'assistant-response', label: 'Assistant response', responseId, source: 'voice' };
		} else if (sourceLower === 'voice' && typeLower.startsWith('input_audio_buffer')) {
			const bucket = data.item_id || data.item?.id || msg.id || `input-${index}`;
			groupKey = `input:${bucket}`;
			defaults = { kind: 'user-speech', label: 'User speech', itemId: bucket, source: msg.source };
		} else if (data.call_id || data.item?.call_id) {
			const callId = data.call_id || data.item?.call_id;
			groupKey = `call:${callId}`;
			defaults = { kind: 'tool-call', label: 'Tool call', callId, source: msg.source };
		} else if (sourceLower === 'controller' && typeLower === 'voice_forward') {
			const bucket = msg.timestamp || `forward-${index}`;
			groupKey = `forward:${bucket}`;
			defaults = { kind: 'controller-forward', label: 'Forwarded narration', source: msg.source };
		} else if (sourceLower === 'controller') {
			groupKey = `controller:${msg.id || `${typeLower}-${index}`}`;
			defaults = { kind: 'generic', label: 'Controller event', source: msg.source };
		} else if (sourceLower === 'nested' || sourceLower === 'nested_agent') {
			groupKey = `nested:${msg.id || `${typeLower}-${index}`}`;
			defaults = { kind: 'generic', label: 'Nested event', source: msg.source };
		} else {
			groupKey = `event:${msg.id || `${typeLower}-${index}`}`;
			defaults = { kind: 'generic', label: 'Event', source: msg.source };
		}

		const group = ensureGroup(groupKey, defaults);
		if (!group.firstTimestamp && msg.timestamp) group.firstTimestamp = msg.timestamp;
		if (msg.timestamp) group.lastTimestamp = msg.timestamp;
		group.events.push(msg);

		if (group.kind === 'assistant-response') {
			switch (typeLower) {
				case 'response.created':
					group.voice = data.response?.voice || group.voice;
					group.modalities = data.response?.modalities || group.modalities;
					group.responseStatus = data.response?.status || group.responseStatus;
					group.responseCreatedAt = msg.timestamp || group.responseCreatedAt;
					break;
				case 'response.audio_transcript.delta':
					if (!group.transcriptChunks) group.transcriptChunks = [];
					if (data.delta) group.transcriptChunks.push(data.delta);
					if (!group.deltaEvents) group.deltaEvents = [];
					group.deltaEvents.push(msg);
					break;
				case 'response.audio_transcript.done':
					if (data.transcript) group.finalTranscript = data.transcript;
					break;
				case 'response.content_part.done':
					if (!group.finalTranscript && data.part?.transcript) {
						group.finalTranscript = data.part.transcript;
					}
					break;
				case 'response.done':
					group.responseStatus = data.response?.status || group.responseStatus;
					group.responseStatusReason = data.response?.status_details?.reason || group.responseStatusReason;
					group.responseUsage = data.response?.usage || group.responseUsage;
					group.responseCompletedAt = msg.timestamp || group.responseCompletedAt;
					break;
				case 'rate_limits.updated':
					group.lastRateLimit = data.rate_limits?.[0] || group.lastRateLimit;
					break;
				default:
					break;
			}
		} else if (group.kind === 'user-speech') {
			switch (typeLower) {
				case 'input_audio_buffer.speech_started':
					group.audioStart = data.audio_start_ms;
					break;
				case 'input_audio_buffer.speech_stopped':
					group.audioEnd = data.audio_end_ms;
					break;
				case 'conversation.item.created': {
					if (Array.isArray(data.item?.content)) {
						const transcripts = data.item.content.map((c) => c?.transcript).filter(Boolean);
						if (transcripts.length) group.transcript = transcripts.join(' ');
					}
					break;
				}
				default:
					break;
			}
		} else if (group.kind === 'tool-call') {
			switch (typeLower) {
				case 'response.function_call':
				case 'response.function_call.arguments.delta':
				case 'response.function_call_arguments.delta':
					if (!group.functionCall) group.functionCall = { name: data.name || data.function_call?.name, args: '' };
					if (data.delta) group.functionCall.args += data.delta;
					if (data.arguments) group.functionCall.args += data.arguments;
					break;
				case 'response.function_call.completed':
				case 'response.function_call_arguments.done':
					if (!group.functionCall) {
						group.functionCall = { name: data.name || data.function_call?.name, args: '' };
					}
					if (data.arguments) group.functionCall.args = data.arguments;
					break;
				default:
					break;
			}
		}

		const summary = summarizeEvent({ ...msg, data });
		if (summary) {
			group.timeline.push({
				id: msg.id ?? `${group.events.length}-${index}`,
				label: summary,
				timestamp: msg.timestamp,
				source: msg.source,
			});
		}
	});

	groupsList.forEach((group) => {
		const transcript = group.finalTranscript
			|| (Array.isArray(group.transcriptChunks) ? group.transcriptChunks.join('') : '')
			|| group.transcript
			|| '';
		if (transcript) group.summary = truncateText(transcript, 280);

		// Extract summaries for disconnected mode events
		if (group.source === 'disconnected' && group.events.length > 0) {
			const firstEvent = group.events[0];
			const eventData = firstEvent.data || {};
			const eventType = (firstEvent.type || '').toLowerCase();

			if (eventType === 'disconnected_user_audio') {
				group.summary = eventData.transcript ? truncateText(eventData.transcript, 280) : 'Audio message';
			} else if (eventType === 'disconnected_user_text') {
				group.summary = eventData.text ? truncateText(eventData.text, 280) : 'Text message';
			} else if (eventType === 'disconnected_assistant_response') {
				group.summary = eventData.text ? truncateText(eventData.text, 280) : 'Response';
				if (eventData.has_audio) {
					group.badges.push({ label: 'Audio' });
				}
			} else if (eventType === 'disconnected_tool_call') {
				const toolName = eventData.tool || 'unknown';
				const success = eventData.result?.success;
				group.summary = `${toolName}: ${success ? 'Success' : 'Failed'}`;
				if (eventData.result?.error) {
					group.summary += ` - ${truncateText(eventData.result.error, 100)}`;
				}
				group.badges.push({ label: `Tool: ${toolName}` });
			}
		}

		if (group.kind === 'tool-call' && group.functionCall) {
			const chunks = group.functionCall.args ? truncateText(group.functionCall.args, 200) : '';
			group.summary = chunks || group.summary || 'Tool call';
			if (group.functionCall.name) {
				group.badges.push({ label: `Tool: ${group.functionCall.name}` });
			}
		}
		if (group.kind === 'assistant-response' && group.responseStatus) {
			group.badges.push({ label: `Status: ${group.responseStatus}` });
		}
		if (group.responseUsage?.total_tokens != null) {
			group.badges.push({ label: `${group.responseUsage.total_tokens} tokens` });
		}
		if (group.modalities?.length) {
			group.badges.push({ label: `Modalities: ${group.modalities.join('/')}` });
		}
		if (group.audioStart != null && group.audioEnd != null) {
			const duration = formatDurationMs(group.audioStart, group.audioEnd);
			if (duration) group.badges.push({ label: `Duration ${duration}` });
		}
		group.timeSubtitle = buildTimeSubtitle(group.firstTimestamp, group.lastTimestamp, formatTimestamp);
	});

	return groupsList;
};

const ConversationHistoryGroup = ({ group, formatTimestamp }) => {
	const Icon = groupIconKind(group.kind);
	const deltaSummary = (group.deltaEvents && group.deltaEvents.length)
		? {
				count: group.deltaEvents.length,
				text: group.finalTranscript || (group.transcriptChunks ? group.transcriptChunks.join('') : ''),
				events: group.deltaEvents,
			}
		: null;

	return (
		<Accordion
			disableGutters
			elevation={0}
			sx={{
				border: '1px solid',
				borderColor: 'divider',
				borderRadius: 1,
				backgroundColor: 'rgba(255, 255, 255, 0.02)',
				'&:before': {
					display: 'none',
				},
			}}
		>
			<AccordionSummary
				expandIcon={<ExpandMoreIcon />}
				sx={{
					px: 2,
					backgroundColor: 'transparent',
				}}
			>
				<Stack spacing={0.75} sx={{ width: '100%' }}>
					<Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ '& .MuiChip-root': { mr: 0.5, mb: 0.5 } }}>
						<Chip icon={<Icon fontSize="small" />} size="small" label={group.label} variant="outlined" />
						{group.source && <Chip size="small" label={group.source} variant="outlined" />}
						{group.badges.map((badge, idx) => (
							<Chip key={`${group.key}-badge-${idx}`} size="small" label={badge.label} variant="outlined" />
						))}
						<Box sx={{ flexGrow: 1 }} />
						{group.timeSubtitle && (
							<Typography variant="caption" color="text.secondary">{group.timeSubtitle}</Typography>
						)}
					</Stack>
					{group.summary && (
						<Typography variant="body2" color="text.secondary">{group.summary}</Typography>
					)}
				</Stack>
			</AccordionSummary>
			<AccordionDetails
				sx={{
					px: 2,
					pb: 2,
					backgroundColor: 'transparent',
				}}
			>
				<Stack spacing={1.5}>
					{deltaSummary && (
						<HistoryDeltaGroup entry={deltaSummary} />
					)}
					{group.timeline.length > 0 && (
						<Stack spacing={1}>
							{group.timeline.map((item) => (
								<Typography key={item.id} variant="body2" color="text.secondary">
									{item.timestamp ? `${formatTimestamp(item.timestamp)} · ` : ''}{item.label}
								</Typography>
							))}
						</Stack>
					)}
					<Divider />
					<Stack spacing={1.25}>
						{group.events.map((msg, idx) => (
							<HistoryEventRow
								key={msg.id ?? `${group.key}-event-${idx}`}
								event={{ msg, summary: summarizeEvent(msg) }}
								formatTimestamp={formatTimestamp}
							/>
						))}
					</Stack>
				</Stack>
			</AccordionDetails>
		</Accordion>
	);
};

const ConversationHistory = ({
	messages = [],
	conversationLoading = false,
	isRunning = false,
	formatTimestamp: formatTimestampProp,
}) => {
	const formatter = formatTimestampProp || fallbackFormatTimestamp;
	const groups = useMemo(() => buildGroupedHistory(messages, formatter), [messages, formatter]);
	const virtuosoRef = useRef(null);

	useEffect(() => {
		if (virtuosoRef.current && groups.length > 0) {
			virtuosoRef.current.scrollToIndex({
				index: groups.length - 1,
				align: 'end',
				behavior: 'auto'
			});
		}
	}, [groups]);

	const renderGroup = (index, group) => {
		return (
			<Box sx={{ mb: 1.25 }}>
				<ConversationHistoryGroup group={group} formatTimestamp={formatter} />
			</Box>
		);
	};

	return (
		<Box
			sx={{
				p: 2,
				display: 'flex',
				flexDirection: 'column',
				height: "100%",
			}}
		>
			<Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
				{conversationLoading && <CircularProgress size={18} thickness={5} />}
				{isRunning && (
					<Chip size="small" color="success" variant="outlined" label="Live" />
				)}
				{Array.isArray(messages) && messages.length > 0 && (
					<Chip size="small" variant="outlined" label={`${messages.length} event${messages.length === 1 ? '' : 's'}`} />
				)}
			</Stack>

			<Box
				sx={{
					flexGrow: 1,
					pr: 1,
				}}
			>
				{messages.length === 0 && !conversationLoading && (
					<Alert severity="info">No events recorded yet. Start a session to populate the history.</Alert>
				)}

				{groups.length > 0 && (
					<Virtuoso
						ref={virtuosoRef}
						style={{ height: '100%' }}
						data={groups}
						itemContent={renderGroup}
						followOutput="smooth"
					/>
				)}

				{conversationLoading && messages.length === 0 && (
					<Stack spacing={1}>
						<Typography variant="body2" color="text.secondary">Loading conversation history…</Typography>
						<CircularProgress size={24} thickness={5} />
					</Stack>
				)}
			</Box>
		</Box>
	);
};

export default ConversationHistory;
