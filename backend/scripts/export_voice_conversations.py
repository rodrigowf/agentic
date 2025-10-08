#!/usr/bin/env python3
"""Export voice conversation data from the SQLite store into JSON files.

This script walks every conversation stored in ``voice_conversations.db`` and
writes one JSON file per conversation.  Each export file contains the
conversation metadata as well as its ordered list of events, making it easy to
archive, inspect, or migrate the history elsewhere.

Usage examples
--------------

Export using the default database path and write files into
``exports/voice_conversations`` under the backend directory::

    python scripts/export_voice_conversations.py

Specify a custom database path and output directory::

    python scripts/export_voice_conversations.py \
        --db /path/to/voice_conversations.db \
        --out /tmp/voice_exports

The script will create the output directory if it does not exist already.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import sys

# Ensure the backend package root is importable when the script is run directly.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from voice_conversation_store import ConversationStore, DEFAULT_DB_PATH


def _dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")  # POSIX-friendly newline at EOF


def export_conversations(db_path: str, output_dir: Path) -> int:
    store = ConversationStore(db_path)
    conversations: List[Dict[str, Any]] = store.list_conversations()
    export_count = 0

    for convo in conversations:
        convo_id = convo["id"]
        events = store.list_events(convo_id)
        export_payload: Dict[str, Any] = {
            "conversation": convo,
            "events": events,
        }
        output_path = output_dir / f"{convo_id}.json"
        _dump_json(output_path, export_payload)
        export_count += 1

    return export_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        dest="db_path",
        default=DEFAULT_DB_PATH,
        help="Path to voice_conversations.db (defaults to the application's configured database).",
    )
    parser.add_argument(
        "--out",
        dest="output_dir",
        default=Path(__file__).resolve().parent.parent / "exports" / "voice_conversations",
        type=Path,
        help="Directory where JSON exports will be written (created if missing).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = os.path.abspath(args.db_path)
    output_dir = args.output_dir

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    exported = export_conversations(db_path, output_dir)
    print(f"Exported {exported} conversation{'s' if exported != 1 else ''} to {output_dir}")


if __name__ == "__main__":
    main()
