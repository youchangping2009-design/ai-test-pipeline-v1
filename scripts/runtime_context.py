#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class ModelRuntimeConfig:
    model: str | None
    model_source: str | None
    api_key: str | None
    api_key_source: str | None
    base_url: str
    base_url_source: str
    adapter: str | None


def _string(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return None


def _read_runtime_context_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _detect_host_adapter(env: Mapping[str, str]) -> str | None:
    return _string(env.get("ATP_HOST_ADAPTER"))


def _load_adapter_values(adapter: str | None, env: Mapping[str, str]) -> dict[str, str | None]:
    if not adapter:
        return {}

    module_name = f"tool_adapters.{adapter}.runtime_context"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return {}

    resolver = getattr(module, "resolve_runtime_values", None)
    if resolver is None:
        return {}

    payload = resolver(env)
    return payload if isinstance(payload, dict) else {}


def resolve_runtime_context(
    explicit_model: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ModelRuntimeConfig:
    active_env = env or os.environ

    runtime_model = _string(active_env.get("ATP_MODEL")) or _string(active_env.get("ATP_ACTIVE_MODEL"))
    runtime_api_key = _string(active_env.get("ATP_API_KEY")) or _string(active_env.get("ATP_MODEL_API_KEY"))
    runtime_base_url = _string(active_env.get("ATP_BASE_URL")) or _string(active_env.get("ATP_MODEL_BASE_URL"))

    compatibility_model = _string(active_env.get("OPENAI_MODEL"))
    compatibility_api_key = _string(active_env.get("OPENAI_API_KEY"))
    compatibility_base_url = _string(active_env.get("OPENAI_BASE_URL"))

    runtime_file_payload: dict = {}
    runtime_file = _string(active_env.get("ATP_RUNTIME_CONTEXT_FILE"))
    if runtime_file:
        runtime_file_payload = _read_runtime_context_file(Path(runtime_file).expanduser())

    adapter = _detect_host_adapter(active_env)
    adapter_payload = _load_adapter_values(adapter, active_env)

    model = (
        _string(explicit_model)
        or runtime_model
        or _string(runtime_file_payload.get("model"))
        or compatibility_model
        or _string(adapter_payload.get("model"))
    )
    if _string(explicit_model):
        model_source = "explicit_argument"
    elif runtime_model:
        model_source = "env.ATP_MODEL"
    elif _string(runtime_file_payload.get("model")):
        model_source = "runtime_context_file.model"
    elif compatibility_model:
        model_source = "compat_env.OPENAI_MODEL"
    else:
        model_source = _string(adapter_payload.get("model_source"))

    api_key = (
        runtime_api_key
        or _string(runtime_file_payload.get("api_key"))
        or compatibility_api_key
        or _string(adapter_payload.get("api_key"))
    )
    if runtime_api_key:
        api_key_source = "env.ATP_API_KEY"
    elif _string(runtime_file_payload.get("api_key")):
        api_key_source = "runtime_context_file.api_key"
    elif compatibility_api_key:
        api_key_source = "compat_env.OPENAI_API_KEY"
    else:
        api_key_source = _string(adapter_payload.get("api_key_source"))

    base_url = (
        runtime_base_url
        or _string(runtime_file_payload.get("base_url"))
        or compatibility_base_url
        or _string(adapter_payload.get("base_url"))
        or ""
    )
    if runtime_base_url:
        base_url_source = "env.ATP_BASE_URL"
    elif _string(runtime_file_payload.get("base_url")):
        base_url_source = "runtime_context_file.base_url"
    elif compatibility_base_url:
        base_url_source = "compat_env.OPENAI_BASE_URL"
    elif _string(adapter_payload.get("base_url")):
        base_url_source = _string(adapter_payload.get("base_url_source")) or "adapter.base_url"
    else:
        base_url_source = "unset"

    return ModelRuntimeConfig(
        model=model,
        model_source=model_source,
        api_key=api_key,
        api_key_source=api_key_source,
        base_url=base_url,
        base_url_source=base_url_source,
        adapter=_string(adapter_payload.get("adapter")),
    )
