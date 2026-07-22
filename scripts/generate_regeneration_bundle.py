#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from execute_regeneration_bundle import validate_bundle
from runtime_context import resolve_runtime_context


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = [
    "inputs/requirement_summary.md",
    "inputs/source_manifest.json",
    "evidence/evidence_inventory.json",
    "structured_prd/structured_prd.json",
    "traceability/traceability_matrix.json",
    "testcases/case_plan.json",
    "testcases/testcases_main.md",
    "testcases/testcases.md",
    "reviews/review_record.md",
]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_bundle_path(item_root: Path) -> Path:
    return item_root / ".generation" / "latest" / "regeneration_bundle.json"


def generation_dir(item_root: Path) -> Path:
    return item_root / ".generation" / "latest"


def load_run_manifest(item_root: Path) -> dict:
    manifest_path = generation_dir(item_root) / "run_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            "缺少 run_manifest.json，请先执行 prepare_regeneration_run.py 生成任务包"
        )
    return read_json(manifest_path)


def build_existing_bundle(item_root: Path, run_manifest: dict) -> dict:
    artifacts: dict[str, str] = {}
    missing: list[str] = []
    requested_paths = [item_root / suffix for suffix in REQUIRED_ARTIFACTS]
    for relative_path in run_manifest.get("cleanup_targets", []):
        artifact_path = ROOT / relative_path
        if artifact_path not in requested_paths:
            requested_paths.append(artifact_path)

    for artifact_path in requested_paths:
        if not artifact_path.exists():
            if any(str(artifact_path).endswith(suffix) for suffix in REQUIRED_ARTIFACTS):
                missing.append(rel(artifact_path))
            continue
        artifacts[rel(artifact_path)] = read_text(artifact_path)

    if rel(main_testcases_path := item_root / "testcases" / "testcases_main.md") in missing and (item_root / "testcases" / "testcases.md").exists():
        missing.remove(rel(main_testcases_path))

    if missing:
        raise SystemExit("当前产物不完整，无法生成 existing bundle:\n- " + "\n- ".join(missing))

    compat_testcases_path = item_root / "testcases" / "testcases.md"
    if main_testcases_path.exists() and rel(main_testcases_path) not in artifacts:
        artifacts[rel(main_testcases_path)] = read_text(main_testcases_path)
    if compat_testcases_path.exists() and rel(compat_testcases_path) not in artifacts:
        artifacts[rel(compat_testcases_path)] = read_text(compat_testcases_path)

    cleanup_targets = run_manifest.get("cleanup_targets", [])
    bundle = {
        "provider": "existing",
        "cleanup_targets": cleanup_targets,
        "artifacts": artifacts,
    }
    validate_or_exit(bundle)
    return bundle


def build_generation_prompt(item_root: Path, run_manifest: dict) -> str:
    task_files = run_manifest.get("task_files", [])
    sections: list[str] = [
        "# Regeneration Bundle Generation Task",
        "",
        "You are generating a regeneration bundle for AI Test Pipeline.",
        "Return ONLY a JSON object with keys: cleanup_targets, artifacts.",
        "The artifacts object keys must be repository-relative output paths, and values must be full file contents.",
        "Do not include markdown fences or explanations.",
        "",
        "## Run Manifest",
        json.dumps(run_manifest, ensure_ascii=False, indent=2),
    ]

    for task_file in task_files:
        task_path = ROOT / task_file
        if task_path.exists():
            sections.extend(["", f"## Task File: {task_file}", read_text(task_path)])

    inputs_dir = item_root / "inputs"
    input_files = sorted(path for path in inputs_dir.iterdir() if path.is_file()) if inputs_dir.exists() else []
    sections.append("\n## Input File Inventory")
    for input_file in input_files:
        sections.append(f"- {rel(input_file)}")

    return "\n".join(sections)


def call_openai_provider(item_root: Path, run_manifest: dict, model: str | None) -> dict:
    runtime = resolve_runtime_context(explicit_model=model)
    api_key = runtime.api_key
    model_name = runtime.model
    if not api_key:
        raise SystemExit(
            "运行时上下文未提供 API Key，请通过当前宿主会话、本地环境变量、"
            "runtime context 文件或适配层配置提供"
        )
    if not model_name:
        raise SystemExit(
            "运行时上下文未解析到模型名，请通过当前宿主会话、ATP_MODEL、"
            "runtime context 文件或兼容参数提供"
        )

    prompt = build_generation_prompt(item_root, run_manifest)
    request_body = {
        "model": model_name,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_object"
            }
        },
    }
    request = urllib.request.Request(
        runtime.base_url.rstrip("/") + "/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"openai provider 请求失败: {exc}") from exc

    output_text = extract_response_text(payload)
    try:
        bundle = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"openai provider 未返回合法 JSON bundle: {exc}") from exc

    validate_or_exit(bundle)
    bundle["provider"] = "openai"
    bundle["model"] = model_name
    bundle["model_source"] = runtime.model_source
    bundle["base_url_source"] = runtime.base_url_source
    bundle["runtime_adapter"] = runtime.adapter
    return bundle


def call_command_provider(
    item_root: Path,
    run_manifest: dict,
    command_text: str | None,
) -> dict:
    if not command_text or not command_text.strip():
        raise SystemExit("command provider 需要通过 --generator-command 提供本地生成命令")

    output_path = default_bundle_path(item_root)
    run_manifest_path = generation_dir(item_root) / "run_manifest.json"
    env = os.environ.copy()
    env.update(
        {
            "ATP_REPO_ROOT": str(ROOT),
            "ATP_WORK_ITEM_ROOT": str(item_root),
            "ATP_PROJECT_CODE": run_manifest.get("project_code", ""),
            "ATP_WORK_ITEM_ID": run_manifest.get("work_item_id", ""),
            "ATP_RUN_MANIFEST": str(run_manifest_path),
            "ATP_OUTPUT_BUNDLE": str(output_path),
        }
    )

    command = shlex.split(command_text)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    if result.returncode != 0:
        raise SystemExit(
            "command provider 执行失败:\n"
            f"命令: {command_text}\n"
            f"输出:\n{output.strip()}"
        )

    if output_path.exists():
        bundle = read_json(output_path)
    else:
        stripped = output.strip()
        if not stripped:
            raise SystemExit(
                "command provider 未输出 bundle 文件，也未在 stdout 返回 JSON"
            )
        try:
            bundle = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(
                "command provider stdout 不是合法 JSON，且未写出 bundle 文件"
            ) from exc

    validate_or_exit(bundle)
    bundle["provider"] = "command"
    bundle["generator_command"] = command_text
    return bundle


def extract_response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if not chunks:
        raise SystemExit("openai provider 响应中未找到文本输出")
    return "".join(chunks)


def validate_or_exit(bundle: dict) -> None:
    cleanup_targets = bundle.get("cleanup_targets", [])
    artifacts = bundle.get("artifacts", {})
    if not isinstance(cleanup_targets, list) or not isinstance(artifacts, dict):
        raise SystemExit("bundle 结构非法：cleanup_targets 必须是数组，artifacts 必须是对象")
    errors = validate_bundle(
        cleanup_targets,
        artifacts,
        str(bundle.get("work_item_level", "")).strip().upper() or None,
    )
    if errors:
        raise SystemExit("bundle 校验失败:\n- " + "\n- ".join(errors))


def run_execute(project_code: str, work_item_id: str, bundle_path: Path) -> int:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "execute_regeneration_bundle.py"),
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
        "--bundle",
        str(bundle_path),
    ]
    return subprocess.call(command, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成工作项 regeneration bundle，可选直接执行")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument(
        "--provider",
        choices=["existing", "command", "openai"],
        default="existing",
        help="bundle 生成兼容入口；existing 固化当前产物，command 调本地命令，openai 走 HTTP endpoint 兼容实现",
    )
    parser.add_argument(
        "--model",
        required=False,
        help="兼容 HTTP endpoint 入口的覆盖模型名；默认从运行时上下文与宿主适配层解析",
    )
    parser.add_argument(
        "--generator-command",
        required=False,
        help="command provider 使用的本地命令；可读取 ATP_RUN_MANIFEST / ATP_OUTPUT_BUNDLE 等环境变量",
    )
    parser.add_argument("--output", required=False, help="bundle 输出路径，默认 .generation/latest/regeneration_bundle.json")
    parser.add_argument("--execute", action="store_true", help="bundle 生成后立即执行重生成")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = work_item_root(project_code, work_item_id)
    if not item_root.exists():
        print(f"工作项不存在: {item_root}", file=sys.stderr)
        return 1

    run_manifest = load_run_manifest(item_root)
    if args.provider == "existing":
        bundle = build_existing_bundle(item_root, run_manifest)
    elif args.provider == "command":
        bundle = call_command_provider(item_root, run_manifest, args.generator_command)
    else:
        bundle = call_openai_provider(item_root, run_manifest, args.model)
    bundle["work_item_level"] = run_manifest.get("work_item_level", "M")
    validate_or_exit(bundle)

    output_path = Path(args.output).resolve() if args.output else default_bundle_path(item_root)
    write_json(output_path, bundle)
    print(f"已生成 regeneration bundle: {output_path}")

    if args.execute:
        return run_execute(project_code, work_item_id, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
