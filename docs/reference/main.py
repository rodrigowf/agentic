import os
import json
import time
from typing import List, Optional, Any, Dict
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from requests import RequestException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))  # simple per-IP limit
DEFAULT_TIMEOUT = 45  # seconds external call timeout

# In-memory rate limit store: {ip: [timestamps]}
_rate_buckets: Dict[str, list] = {}

def _check_rate_limit(ip: str):
    now = time.time()
    bucket = _rate_buckets.setdefault(ip, [])
    # prune entries older than 60s
    cutoff = now - 60
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try later.")
    bucket.append(now)

OPENAI_BASE = "https://api.openai.com/v1"
GEMINI_MODELS_LIST = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_GENERATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
OPENAI_REALTIME_SESSIONS = "https://api.openai.com/v1/realtime/sessions"

OPENAI_EXTRA_HEADERS = {
    # Future-proofing realtime / beta features (ignored if not needed)
    "OpenAI-Beta": "realtime=v1"
}

app = FastAPI(title="Tutor Backend", version="0.1.1")

# CORS (development friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BoardSection(BaseModel):
    section_id: str
    content: str
    # title removed; headings must appear inside content HTML

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    provider: str
    model: str
    messages: List[ChatMessage]
    board_state: Optional[List[BoardSection]] = None

# Utility for consistent error payload
def _external_call(fn_desc: str, func):
    try:
        return func()
    except HTTPException:
        raise
    except RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream {fn_desc} network error: {e}")
    except Exception as e:  # pragma: no cover (safety net)
        raise HTTPException(status_code=500, detail=f"Unexpected {fn_desc} error") from e

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/models")
async def list_models(provider: str, request: Request):
    _check_rate_limit(request.client.host if request.client else "anon")
    provider_l = provider.lower()
    if provider_l == "openai":
        def call():
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            r = requests.get(f"{OPENAI_BASE}/models", headers=headers, timeout=15)
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch OpenAI models")
            data = r.json().get("data", [])
            model_ids = [m.get("id") for m in data if m.get("id", "").startswith("gpt")] or [m.get("id") for m in data]
            return {"models": model_ids}
        return _external_call("openai models", call)
    elif provider_l == "gemini":
        def call():
            r = requests.get(f"{GEMINI_MODELS_LIST}?key={GEMINI_API_KEY}", timeout=15)
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch Gemini models")
            models = r.json().get("models", [])
            model_ids = []
            for m in models:
                name = m.get("name", "")
                if name.startswith("models/"):
                    name = name.split("/", 1)[1]
                model_ids.append(name)
            return {"models": model_ids}
        return _external_call("gemini models", call)
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")

@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    _check_rate_limit(request.client.host if request.client else "anon")
    provider = req.provider.lower()
    if provider == "openai":
        def call():
            url = f"{OPENAI_BASE}/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
                **OPENAI_EXTRA_HEADERS,
            }
            # System board context message
            board_context = "[]"
            if req.board_state:
                try:
                    board_context = json.dumps([
                        {"id": b.section_id, "content": b.content} for b in req.board_state
                    ])
                except Exception:
                    pass
            system_preamble = (
                "You are an expert teaching assistant that maintains an interactive learning board. "
                "Each board section is stored and rendered RAW (only wrapped in a div with the given id) directly into the DOM. "
                "When you modify a section you must ALWAYS call one of the provided functions. "
                "For upserts, return COMPLETE self-contained HTML SNIPPETS for that section only (do NOT include <html>, <head>, or <body>). "
                "You may include heading elements, inline <style> scoped to that snippet, and safe inline <script> for lightweight interactivity, and <canvas> where helpful for visual demos. "
                "Prefer progressive enhancement and avoid external network requests, remote scripts, eval, alerts, or navigation. "
                "Use semantic HTML5 (section/article/figure), ARIA where appropriate, and Material Design 3 utility/classes (MDUI v2) which are available globally. "
                "If adding JS, keep it minimal and idempotent (guard against multiple executions). "
                "If extending an existing section, use mode='append'. Otherwise default to replace. "
                "Always choose concise kebab-case section ids. "
                "Current board JSON (id/content): " + board_context + "."
            )
            # Prepend system message only once per request
            messages_payload = [{"role": "system", "content": system_preamble}] + [m.model_dump() for m in req.messages]
            functions = [
                {
                    "name": "upsert_board_section",
                    "description": "Create or update a board section (append or replace) with complete HTML snippet (headings inline).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "section_id": {"type": "string", "description": "Unique kebab-case id"},
                            "content": {"type": "string", "description": "Full HTML snippet for the section (no <html>/<body>)"},
                            "mode": {"type": "string", "enum": ["replace", "append"], "description": "replace or append content"}
                        },
                        "required": ["section_id", "content"]
                    }
                },
                {
                    "name": "delete_board_section",
                    "description": "Delete a board section by id.",
                    "parameters": {
                        "type": "object",
                        "properties": {"section_id": {"type": "string"}},
                        "required": ["section_id"]
                    }
                }
            ]
            payload = {
                "model": req.model,
                "messages": messages_payload,
                "functions": functions,
                "function_call": "auto"
            }
            r = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail="OpenAI error: " + r.text[:500])
            resp = r.json()
            choice = resp.get("choices", [{}])[0].get("message", {})
            result: Dict[str, Any] = {"provider": provider, "model": req.model}
            if "function_call" in choice:
                fc = choice["function_call"]
                try:
                    args = json.loads(fc.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {"raw": fc.get("arguments")}
                # Apply server-side if recognized
                if fc.get('name') == 'upsert_board_section' and 'section_id' in args and 'content' in args:
                    upsert_section(args['section_id'], args['content'], args.get('title'), args.get('mode','replace'))
                elif fc.get('name') == 'delete_board_section' and 'section_id' in args:
                    delete_section(args['section_id'])
                result["function_call"] = {"name": fc.get("name"), "args": args}
            else:
                result["answer"] = choice.get("content")
            result['board'] = load_board()
            return result
        return _external_call("openai chat", call)
    elif provider == "gemini":
        def call():
            url = GEMINI_GENERATE.format(model=req.model, key=GEMINI_API_KEY)
            user_parts = []
            if req.board_state:
                try:
                    board_context = json.dumps([
                        {"id": b.section_id, "title": b.title} for b in req.board_state
                    ])
                except Exception:
                    board_context = "[]"
                user_parts.append("[BOARD_CONTEXT] " + board_context)
            for m in req.messages[-16:]:  # trim context server side too
                prefix = "User" if m.role == "user" else ("Assistant" if m.role == "assistant" else m.role.title())
                user_parts.append(f"{prefix}: {m.content}")
            prompt = "\n".join(user_parts)
            gemini_payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            r = requests.post(url, json=gemini_payload, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail="Gemini error: " + r.text[:500])
            data = r.json()
            text = None
            try:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text")
            except Exception:
                pass
            out = {"provider": provider, "model": req.model, "answer": text, 'board': load_board()}
            return out
        return _external_call("gemini chat", call)
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")

@app.get("/token/openai")
async def get_openai_token(model: str, voice: Optional[str] = None, request: Request = None):
    _check_rate_limit(request.client.host if request and request.client else "anon")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    # Build instructions with board context for realtime session so model can call functions
    board_snapshot = load_board()
    board_context_json = json.dumps(board_snapshot) if board_snapshot else "[]"
    instructions = (
        "You are an expert teaching assistant that maintains an interactive learning board. "
        "Sections are inserted RAW (wrapped only by a div with the given id). All headings, styling and scripts must be inside the HTML 'content' you generate. Return only spoken summaries verbally; structural changes happen via function calls. "
        "When calling upsert_board_section, provide a COMPLETE HTML snippet (no <html>/<body>) that may include headings, inline <style>, minimal safe <script>, <canvas>, and uses Material Design 3 (MDUI) classes. "
        "Avoid external fetches or dangerous APIs. Keep JS idempotent. Use mode='append' for additive updates; otherwise replace. "
        "Always use kebab-case section ids."
    )
    tools = [
        {
            "type": "function",
            "name": "upsert_board_section",
            "description": "Create or update a board section (append or replace) with full inline HTML (headings inline).",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_id": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["replace", "append"], "default": "replace"}
                },
                "required": ["section_id", "content"]
            }
        },
        {
            "type": "function",
            "name": "delete_board_section",
            "description": "Delete a board section by id.",
            "parameters": {
                "type": "object",
                "properties": {"section_id": {"type": "string"}},
                "required": ["section_id"]
            }
        }
    ]
    payload: Dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "modalities": ["audio", "text"],
        "tools": tools,
        "tool_choice": "auto"
    }
    if voice:
        payload["voice"] = voice
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        **OPENAI_EXTRA_HEADERS,
    }
    def call():
        r = requests.post(OPENAI_REALTIME_SESSIONS, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to create realtime session: {r.text[:300]}")
        data = r.json()
        token = data.get("client_secret", {}).get("value")
        if not token:
            raise HTTPException(status_code=500, detail="No client_secret returned")
        return {"ephemeral_token": token}
    return _external_call("openai realtime session", call)

@app.get("/token/gemini")
async def get_gemini_token():
    # Still not implemented; frontend hides voice for Gemini.
    raise HTTPException(status_code=501, detail="Gemini voice not implemented")

BOARD_FILE = os.path.join(os.path.dirname(__file__), 'board_state.json')
_board_lock = threading.Lock()

def load_board() -> List[Dict[str, Any]]:
    if not os.path.exists(BOARD_FILE):
        return []
    try:
        with open(BOARD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_board(data: List[Dict[str, Any]]):
    with _board_lock:
        with open(BOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def upsert_section(section_id: str, content: str, title: Optional[str], mode: str = 'replace') -> Dict[str, Any]:
    # title param retained for call signature compatibility but ignored
    board = load_board()
    for sec in board:
        if sec.get('section_id') == section_id:
            if mode == 'append':
                sec['content'] = sec.get('content', '') + content
            else:
                sec['content'] = content
            save_board(board)
            return sec
    new_sec = { 'section_id': section_id, 'content': content }
    board.append(new_sec)
    save_board(board)
    return new_sec

def delete_section(section_id: str) -> bool:
    board = load_board()
    new_board = [s for s in board if s['section_id'] != section_id]
    changed = len(new_board) != len(board)
    if changed:
        save_board(new_board)
    return changed

@app.get('/board')
async def get_board():
    return { 'board': load_board() }

class UpsertBody(BaseModel):
    section_id: str
    content: str
    mode: Optional[str] = "replace"

@app.post('/board/upsert')
async def board_upsert(body: UpsertBody):
    print('[Tutor][backend] Board upsert via REST:', body.section_id)
    upsert_section(body.section_id, body.content, None, body.mode or 'replace')
    board_now = load_board()
    print('[Tutor][backend] Board size now', len(board_now))
    return { 'board': board_now }

@app.delete('/board/{section_id}')
async def board_delete(section_id: str):
    print('[Tutor][backend] Board delete via REST:', section_id)
    delete_section(section_id)
    board_now = load_board()
    print('[Tutor][backend] Board size now', len(board_now))
    return { 'board': board_now }

