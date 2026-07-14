#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def _string(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _codex_home(env: Mapping[str, str]) -> Path:
    raw_home = _string(env.get("CODEX_HOME"))
    return Path(raw_home).expanduser() if raw_home else Path.home() / ".codex"


def _read_codex_config(env: Mapping[str, str]) -> dict:
    config_path = _codex_home(env) / "config.toml"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _config_string(config: dict, *path: str) -> str | None:
    current: object = config
    for segment in path:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return _string(current)


def _find_session_file(thread_id: str, env: Mapping[str, str]) -> Path | None:
    sessions_root = _codex_home(env) / "sessions"
    if not sessions_root.exists():
        return None
    matches = sorted(sessions_root.rglob(f"*{thread_id}.jsonl"))
    return matches[-1] if matches else None


def _read_thread_model(thread_id: str, env: Mapping[str, str]) -> tuple[str | None, str | None]:
    session_path = _find_session_file(thread_id, env)
    if session_path is None:
        return None, None

    resolved_model: str | None = None
    source: str | None = None
    try:
        with session_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                payload_type = payload.get("type")
                if payload_type == "turn_context":
                    model = _string(payload.get("payload", {}).get("model"))
                    if model:
                        resolved_model = model
                        source = "codex_thread_context"
                elif payload_type == "session_meta" and resolved_model is None:
                    model = _string(payload.get("payload", {}).get("model"))
                    if model:
                        resolved_model = model
                        source = "codex_session_meta"
    except OSError:
        return None, None

    return resolved_model, source


def resolve_runtime_values(env: Mapping[str, str]) -> dict[str, str | None]:
    config = _read_codex_config(env)

    thread_id = _string(env.get("CODEX_THREAD_ID"))
    model: str | None = None
    model_source: str | None = None
    if thread_id:
        model, model_source = _read_thread_model(thread_id, env)

    if model is None:
        model = _config_string(config, "model")
        model_source = "codex_config.model" if model else None

    api_key = _config_string(config, "providers", "openai", "api_key")
    api_key_source = "codex_config.providers.openai.api_key" if api_key else None

    base_url = _config_string(config, "providers", "openai", "base_url")
    base_url_source = "codex_config.providers.openai.base_url" if base_url else None

    return {
        "adapter": "codex",
        "model": model,
        "model_source": model_source,
        "api_key": api_key,
        "api_key_source": api_key_source,
        "base_url": base_url,
        "base_url_source": base_url_source,
    }
