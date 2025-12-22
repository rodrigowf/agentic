"""
claude_oauth.py
================

Claude Code OAuth authentication module.
Manages OAuth flow for Claude.ai subscribers using the Claude CLI's `setup-token` command.

This module provides:
- OAuth credentials checking from ~/.claude/.credentials.json
- OAuth flow management via the Claude CLI
- Real-time status updates via Server-Sent Events (SSE)

The OAuth flow works by:
1. Spawning `claude setup-token` in a PTY (pseudo-terminal)
2. Extracting the authentication URL from the CLI output
3. Waiting for the user to authenticate and paste the code
4. Forwarding the code to the CLI process
5. Verifying credentials were saved successfully
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Set
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Credentials file location
CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"


class OAuthStatus(str, Enum):
    """OAuth flow status states."""
    IDLE = "idle"
    WAITING_FOR_URL = "waiting_for_url"
    URL_READY = "url_ready"
    WAITING_FOR_CODE = "waiting_for_code"
    AUTHENTICATING = "authenticating"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OAuthCredentials:
    """OAuth credentials from Claude CLI."""
    access_token: str
    refresh_token: str
    expires_at: int
    scopes: list
    subscription_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None


@dataclass
class OAuthFlowStatus:
    """Current OAuth flow status."""
    status: OAuthStatus
    auth_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status.value,
        }
        if self.auth_url:
            result["authUrl"] = self.auth_url
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        if self.credentials:
            result["credentials"] = self.credentials
        return result


class ClaudeOAuthManager:
    """Manages Claude OAuth authentication flow."""

    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._current_status = OAuthFlowStatus(status=OAuthStatus.IDLE)
        self._listeners: Set[Callable[[OAuthFlowStatus], None]] = set()
        self._output_buffer = ""
        self._auth_url: Optional[str] = None

    def _broadcast(self, status: OAuthFlowStatus) -> None:
        """Broadcast status update to all listeners."""
        self._current_status = status
        for listener in list(self._listeners):
            try:
                listener(status)
            except Exception as e:
                logger.error(f"[CLAUDE-OAUTH] Listener error: {e}")

    def subscribe(self, listener: Callable[[OAuthFlowStatus], None]) -> Callable[[], None]:
        """Subscribe to OAuth status updates. Returns unsubscribe function."""
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    def get_status(self) -> OAuthFlowStatus:
        """Get current OAuth flow status."""
        return self._current_status

    async def check_credentials(self) -> Optional[OAuthCredentials]:
        """Check if OAuth credentials exist and are valid."""
        try:
            if not CREDENTIALS_PATH.exists():
                return None

            content = CREDENTIALS_PATH.read_text()
            data = json.loads(content)

            if "claudeAiOauth" in data:
                oauth = data["claudeAiOauth"]
                # Check if token is expired (with 5 minute buffer)
                now = int(datetime.now(timezone.utc).timestamp() * 1000)
                expires_at = oauth.get("expiresAt", 0)

                if expires_at > now + 300000:  # 5 minute buffer
                    return OAuthCredentials(
                        access_token=oauth.get("accessToken", ""),
                        refresh_token=oauth.get("refreshToken", ""),
                        expires_at=expires_at,
                        scopes=oauth.get("scopes", []),
                        subscription_type=oauth.get("subscriptionType"),
                        rate_limit_tier=oauth.get("rateLimitTier"),
                    )
                else:
                    logger.info("[CLAUDE-OAUTH] Token expired or expiring soon")
                    return None
            return None
        except Exception as e:
            logger.warning(f"[CLAUDE-OAUTH] Error checking credentials: {e}")
            return None

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        ansi_pattern = re.compile(r'[\x1b\x9b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]')
        return ansi_pattern.sub('', text)

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract authentication URL from CLI output."""
        clean_text = self._strip_ansi(text)

        url_patterns = [
            r'https://claude\.ai/oauth/authorize[^\s\n]*',
            r'https://claude\.ai/oauth[^\s\n]*',
            r'https://console\.anthropic\.com[^\s\n]*',
        ]

        for pattern in url_patterns:
            match = re.search(pattern, clean_text)
            if match:
                return match.group(0).strip()
        return None

    async def start_oauth_flow(self) -> None:
        """Start the OAuth flow by running `claude setup-token`."""
        if self._process is not None:
            logger.info("[CLAUDE-OAUTH] OAuth flow already in progress")
            return

        self._broadcast(OAuthFlowStatus(
            status=OAuthStatus.WAITING_FOR_URL,
            message="Starting OAuth flow..."
        ))

        # Find claude CLI
        claude_path = shutil.which("claude")
        if not claude_path:
            # Try common paths
            possible_paths = [
                "/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude",
                "/home/rodrigo/miniconda3/envs/agentic/bin/claude",
                "/usr/local/bin/claude",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    claude_path = path
                    break

        if not claude_path:
            self._broadcast(OAuthFlowStatus(
                status=OAuthStatus.ERROR,
                error="Claude CLI not found. Please install Claude Code."
            ))
            return

        # Build command using script for PTY emulation
        import platform
        is_linux = platform.system() == "Linux"
        is_mac = platform.system() == "Darwin"

        if is_linux:
            cmd = ["script", "-q", "-c", f"{claude_path} setup-token", "/dev/null"]
        elif is_mac:
            cmd = ["script", "-q", "/dev/null", claude_path, "setup-token"]
        else:
            cmd = [claude_path, "setup-token"]

        logger.info(f"[CLAUDE-OAUTH] Starting: {' '.join(cmd)}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "TERM": "xterm-256color", "FORCE_COLOR": "0"},
            )

            self._output_buffer = ""
            self._auth_url = None

            # Start reading tasks
            asyncio.create_task(self._read_output())
            asyncio.create_task(self._read_stderr())
            asyncio.create_task(self._wait_for_exit())

        except Exception as e:
            logger.error(f"[CLAUDE-OAUTH] Failed to start process: {e}")
            self._process = None
            self._broadcast(OAuthFlowStatus(
                status=OAuthStatus.ERROR,
                error=str(e)
            ))

    async def _read_output(self) -> None:
        """Read stdout from the OAuth process."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break

                text = line.decode('utf-8', errors='replace')
                self._output_buffer += text
                clean_text = self._strip_ansi(text).strip()

                if clean_text:
                    logger.info(f"[CLAUDE-OAUTH] stdout: {clean_text}")

                # Look for auth URL
                if not self._auth_url:
                    self._auth_url = self._extract_url(self._output_buffer)
                    if self._auth_url:
                        logger.info(f"[CLAUDE-OAUTH] Found auth URL: {self._auth_url}")
                        self._broadcast(OAuthFlowStatus(
                            status=OAuthStatus.URL_READY,
                            auth_url=self._auth_url,
                            message="Please visit the URL to authenticate"
                        ))

                # Check for code prompt
                clean_output = self._strip_ansi(self._output_buffer)
                if any(prompt in clean_output.lower() for prompt in ['paste code here', 'code here', 'enter code']):
                    if self._auth_url and self._current_status.status != OAuthStatus.URL_READY:
                        self._broadcast(OAuthFlowStatus(
                            status=OAuthStatus.URL_READY,
                            auth_url=self._auth_url,
                            message="Paste the authorization code"
                        ))

                # Check for success
                if any(s in clean_output.lower() for s in ['successfully', 'authenticated', 'token saved']):
                    await self._handle_success()

        except Exception as e:
            logger.error(f"[CLAUDE-OAUTH] Error reading stdout: {e}")

    async def _read_stderr(self) -> None:
        """Read stderr from the OAuth process."""
        if not self._process or not self._process.stderr:
            return

        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break

                text = line.decode('utf-8', errors='replace')
                logger.info(f"[CLAUDE-OAUTH] stderr: {text.strip()}")

                # Sometimes URL comes through stderr
                if not self._auth_url:
                    self._auth_url = self._extract_url(text)
                    if self._auth_url:
                        logger.info(f"[CLAUDE-OAUTH] Found auth URL in stderr: {self._auth_url}")
                        self._broadcast(OAuthFlowStatus(
                            status=OAuthStatus.URL_READY,
                            auth_url=self._auth_url,
                            message="Please visit the URL to authenticate"
                        ))

        except Exception as e:
            logger.error(f"[CLAUDE-OAUTH] Error reading stderr: {e}")

    async def _wait_for_exit(self) -> None:
        """Wait for the process to exit."""
        if not self._process:
            return

        try:
            code = await self._process.wait()
            logger.info(f"[CLAUDE-OAUTH] Process exited with code: {code}")
            self._process = None

            if code == 0:
                await self._handle_success()
            elif self._current_status.status != OAuthStatus.SUCCESS:
                self._broadcast(OAuthFlowStatus(
                    status=OAuthStatus.ERROR,
                    error=f"OAuth process exited with code {code}",
                    message=self._output_buffer[-500:] if self._output_buffer else None
                ))
        except Exception as e:
            logger.error(f"[CLAUDE-OAUTH] Error waiting for exit: {e}")
            self._process = None

    async def _handle_success(self) -> None:
        """Handle successful authentication."""
        credentials = await self.check_credentials()
        if credentials:
            self._broadcast(OAuthFlowStatus(
                status=OAuthStatus.SUCCESS,
                message="Authentication successful!",
                credentials={
                    "subscriptionType": credentials.subscription_type,
                    "expiresAt": credentials.expires_at,
                }
            ))
        else:
            self._broadcast(OAuthFlowStatus(
                status=OAuthStatus.ERROR,
                error="Authentication completed but credentials not found"
            ))

    async def send_input(self, code: str) -> None:
        """Send the authorization code to the OAuth process."""
        if self._process and self._process.stdin:
            logger.info("[CLAUDE-OAUTH] Sending authorization code")
            self._process.stdin.write((code + "\n").encode())
            await self._process.stdin.drain()
            self._broadcast(OAuthFlowStatus(
                status=OAuthStatus.AUTHENTICATING,
                message="Verifying code..."
            ))
        else:
            logger.error("[CLAUDE-OAUTH] No active process to send input to")

    async def cancel(self) -> None:
        """Cancel the OAuth flow."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except Exception:
                self._process.kill()
            self._process = None

        self._broadcast(OAuthFlowStatus(status=OAuthStatus.IDLE))


# Global OAuth manager instance
_oauth_manager: Optional[ClaudeOAuthManager] = None


def get_oauth_manager() -> ClaudeOAuthManager:
    """Get the global OAuth manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = ClaudeOAuthManager()
    return _oauth_manager


async def check_claude_auth() -> Dict[str, Any]:
    """
    Check if Claude Code is authenticated and ready to use.
    Checks in order: environment API key, then OAuth credentials.
    """
    manager = get_oauth_manager()

    # 1. Check environment variable for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        logger.info("[CLAUDE-AUTH] ANTHROPIC_API_KEY found in environment")
        return {
            "isAuthenticated": True,
            "method": "api_key",
            "needsLogin": False,
        }

    # 2. Check for OAuth credentials
    credentials = await manager.check_credentials()
    if credentials:
        logger.info("[CLAUDE-AUTH] OAuth credentials found")
        return {
            "isAuthenticated": True,
            "method": "oauth",
            "needsLogin": False,
            "subscriptionType": credentials.subscription_type,
            "expiresAt": credentials.expires_at,
        }

    # No authentication found
    logger.info("[CLAUDE-AUTH] No authentication found, login required")
    return {
        "isAuthenticated": False,
        "needsLogin": True,
        "loginUrl": "https://console.anthropic.com/settings/keys",
        "error": "No API key or OAuth credentials found",
    }


def set_claude_api_key(api_key: str) -> None:
    """Set the API key for Claude authentication."""
    os.environ["ANTHROPIC_API_KEY"] = api_key
    logger.info("[CLAUDE-AUTH] API key set in environment")
