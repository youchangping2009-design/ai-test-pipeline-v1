#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness.hook_dispatcher import (
    HOOK_EVENTS,
    HookConfigurationError,
    HookDispatcher,
)
from harness.state_store import HarnessStateError, StateStore


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="分发已登记的 Harness Hook；不接受任意命令"
    )
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--event", choices=sorted(HOOK_EVENTS), required=True)
    parser.add_argument("--stage-id")
    parser.add_argument("--payload-json", default="{}")
    parser.add_argument("--force-unlock", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = "-".join(args.project_code.strip().split()).upper()
    work_item_id = "-".join(args.work_item_id.strip().split()).upper()
    item_root = (
        ROOT
        / "assets"
        / "projects"
        / project_code
        / "work_items"
        / work_item_id
    )
    try:
        payload = json.loads(args.payload_json)
        if not isinstance(payload, dict):
            raise HarnessStateError("--payload-json 必须是 JSON object")
        store = StateStore(item_root)
        with store.lock(args.run_id, force=args.force_unlock):
            state = store.load(args.run_id)
            dispatcher = HookDispatcher()
            result = dispatcher.dispatch(
                event=args.event,
                state=state,
                run_dir=store.run_dir(args.run_id),
                stage_id=args.stage_id,
                payload=payload,
                event_callback=lambda event_type, event_payload: store.append_event(
                    state,
                    event_type,
                    args.stage_id,
                    event_payload,
                ),
            )
        print(f"run_id: {args.run_id}")
        print(f"hook_event: {args.event}")
        print(f"matched_hooks: {len(result.executions)}")
        print(
            "blocking_failure: "
            + (
                str(result.blocking_failure["execution_id"])
                if result.blocking_failure
                else "-"
            )
        )
        return 1 if result.blocking_failure else 0
    except (
        json.JSONDecodeError,
        HarnessStateError,
        HookConfigurationError,
    ) as exc:
        print(f"hook_dispatch_error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
