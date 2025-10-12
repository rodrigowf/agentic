#!/bin/bash

# Convert ConversationHistory.js to .tsx
sed 's/^import React/import React/' src/features/voice/components/ConversationHistory.js | \
sed "s/export default function ConversationHistory(/export default function ConversationHistory(/" | \
sed "s/ConversationHistoryProps {/ConversationHistoryProps): JSX.Element {/" | \
sed '1i import { ConversationHistoryProps, AgentMessage } from "../../../types";' > src/features/voice/components/ConversationHistory.tsx.tmp

# Move temp file
mv src/features/voice/components/ConversationHistory.tsx.tmp src/features/voice/components/ConversationHistory.tsx

# Convert VoiceDashboard.js to .tsx
sed 's/^export default function VoiceDashboard(/export default function VoiceDashboard(/' src/features/voice/pages/VoiceDashboard.js | \
sed 's/) {/): JSX.Element {/' > src/features/voice/pages/VoiceDashboard.tsx

echo "Converted ConversationHistory and VoiceDashboard"
