#!/usr/bin/env python3
"""Persistent, recoverable project state for story video production."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "story-video-project"
VERSION = "1.0.0"
STATE = "video-project.json"
PLAN = "VIDEO-PLAN.md"
NODES = ["project", "story", "segments", "prompt-pass-1", "assets", "prompt-pass-2", "video-generation", "video-qa", "delivery"]
STATUSES = {"not_started", "in_progress", "waiting_user", "partial", "confirmed", "needs_review", "blocked"}
ITEMS = {"segment": "segments", "asset": "assets", "video": "videos"}
ITEM_STATUSES = {
    "segment": {"planned", "in_progress", "confirmed", "needs_review", "superseded"},
    "asset": {"planned", "generating", "candidate", "approved", "rejected", "needs_review", "superseded"},
    "video": {"planned", "ready", "submitted", "processing", "generated", "qa_failed", "accepted", "provider_failed", "needs_review", "superseded"},
}


class ProjectError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve_inside(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ProjectError(f"Artifact must be inside project: {value}")
    return path


def artifact(root: Path, value: str) -> dict:
    path = resolve_inside(root, value)
    if not path.is_file():
        raise ProjectError(f"Artifact file missing: {value}")
    return {"path": path.relative_to(root).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read(root: Path) -> dict:
    path = root / STATE
    if not path.is_file():
        raise ProjectError(f"Project state missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or data.get("schema_version", "").split(".")[0] != "1":
        raise ProjectError("Unsupported project schema")
    return data


def table(items: dict, columns: list[tuple[str, str]]) -> list[str]:
    header = "| " + " | ".join(title for _, title in columns) + " |"
    result = [header, "| " + " | ".join("---" for _ in columns) + " |"]
    for item_id, item in sorted(items.items()):
        cells = []
        for key, _ in columns:
            value = item_id if key == "id" else item.get(key, "")
            if key == "status" and item.get("review_status") == "needs_review":
                value = f"{value}（待复核）"
            if key == "status" and item.get("binding_review_status") == "needs_review":
                value = f"{value}（参考绑定待复核）"
            cells.append(str(value).replace("|", "\\|").replace("\n", " "))
        result.append("| " + " | ".join(cells) + " |")
    if not items:
        result.append("| " + " | ".join("—" for _ in columns) + " |")
    return result


def render(data: dict) -> str:
    accepted = sum(1 for v in data["videos"].values() if v.get("status") == "accepted" and v.get("review_status") != "needs_review")
    planned_seconds = sum(float(s.get("target_seconds") or 0) for s in data["segments"].values())
    approved_story = data["artifacts"].get("approved_story")
    story_line = (f"- 故事：已批准（[查看故事检查点]({approved_story['path']})）"
                  if approved_story else f"- 创意：{data['idea']}")
    lines = [
        f"# {data['name']}｜视频项目规划",
        "",
        f"- 项目 ID：`{data['project_id']}`",
        story_line,
        f"- 当前节点：`{data['active_node']}`",
        f"- 下一步：{data['next_action']}",
        f"- 目标：{data['settings'].get('goal', '生成并验收全部规划视频片段')}",
        f"- 画幅：{data['settings'].get('aspect_ratio', '待定')}；故事建议时长：{data['settings'].get('total_seconds') or '待故事确认'} 秒；当前片段合计：{planned_seconds:g} 秒",
        f"- 视频完成：{accepted}/{len(data['segments'])} 个片段已验收",
        "",
        "## 任务主线",
        "",
    ]
    for index, node in enumerate(NODES, 1):
        entry = data["nodes"][node]
        lines.append(f"{index}. {node}：**{entry['status']}**" + (f"｜{entry['note']}" if entry.get("note") else ""))
    lines += ["", "## 视频片段", ""]
    lines += table(data["segments"], [("id", "ID"), ("title", "故事任务"), ("target_seconds", "目标秒数"), ("status", "状态")])
    lines += ["", "## 参考资产", ""]
    lines += table(data["assets"], [("id", "ID"), ("name", "名称"), ("kind", "类型"), ("status", "状态")])
    lines += ["", "## 视频生成", ""]
    lines += table(data["videos"], [("id", "ID"), ("segment_id", "片段"), ("status", "状态"), ("task_id", "任务 ID")])
    lines += ["", "## 已登记交付物", ""]
    lines += table(data["artifacts"], [("id", "名称"), ("path", "路径"), ("sha256", "SHA-256")])
    lines += ["", "## 待确认与风险", ""]
    for key in ("pending_decisions", "risks"):
        lines.append(f"### {'待确认' if key == 'pending_decisions' else '风险'}")
        lines.append("")
        lines.extend(f"- {entry}" for entry in data[key]) if data[key] else lines.append("- 无")
        lines.append("")
    lines += [f"更新：{data['updated_at']}", ""]
    return "\n".join(lines)


def save(root: Path, data: dict, event: str) -> None:
    data["updated_at"] = now()
    state_path, plan_path = root / STATE, root / PLAN
    if state_path.exists() or plan_path.exists():
        history = root / "logs" / "history"
        history.mkdir(parents=True, exist_ok=True)
        prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        for path in (state_path, plan_path):
            if path.exists():
                shutil.copy2(path, history / f"{prefix}-{path.name}")
    atomic_text(state_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    atomic_text(plan_path, render(data))
    log = root / "logs" / "events.jsonl"
    with log.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": now(), "event": event, "active_node": data["active_node"]}, ensure_ascii=False) + "\n")


def check_id(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise ProjectError(f"Invalid item ID: {value}")


def check_segment(item: dict) -> None:
    if not isinstance(item.get("title"), str) or not item["title"].strip():
        raise ProjectError("Segment requires a non-empty title")
    seconds = item.get("target_seconds")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ProjectError("Segment target_seconds must be a positive number")
    beats = item.get("visible_beats")
    if beats is not None and (not isinstance(beats, list) or not beats or any(not isinstance(beat, str) or not beat.strip() for beat in beats)):
        raise ProjectError("Segment visible_beats must be a non-empty array of non-empty strings")
    if item.get("status") == "confirmed":
        for key in ("start_state", "end_state", "handoff_out", "director_brief"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ProjectError(f"Confirmed segment requires {key}")
        if beats is None:
            raise ProjectError("Confirmed segment requires visible_beats")
        if not item.get("story_file") and not item.get("story_source"):
            raise ProjectError("Confirmed segment requires a story source")


def check_video_duration(item: dict) -> None:
    source = item.get("download_duration_seconds")
    delivery = item.get("delivery_duration_seconds")
    if source is None or delivery is None:
        return
    for name, value in (("download_duration_seconds", source), ("delivery_duration_seconds", delivery)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ProjectError(f"Video {name} must be a positive number")
    if abs(source - delivery) <= 0.25:
        return
    window = item.get("delivery_source_window_seconds")
    if not isinstance(window, list) or len(window) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in window):
        raise ProjectError("Trimmed video requires delivery_source_window_seconds [start, end]")
    start, end = window
    if start < 0 or end <= start or end > source + 0.25 or abs((end - start) - delivery) > 0.25:
        raise ProjectError("Video delivery window does not match source and delivery durations")
    if not item.get("provider_raw") or not item.get("provider_raw_sha256"):
        raise ProjectError("Trimmed video requires provider_raw and provider_raw_sha256")


def completion_errors(data: dict) -> list[str]:
    if not data["segments"]:
        return ["Project has no planned segments"]
    return [
        f"Segment {segment_id} has no accepted video"
        for segment_id in data["segments"]
        if not any(v.get("segment_id") == segment_id and v.get("status") == "accepted" and v.get("review_status") != "needs_review" for v in data["videos"].values())
    ]


def cmd_init(args: argparse.Namespace) -> dict:
    root = args.project_dir.expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise ProjectError(f"Directory already contains user files: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for part in ("source", "story", "segments", "assets", "videos", "logs"):
        (root / part).mkdir(exist_ok=True)
    data = {
        "schema": SCHEMA, "schema_version": VERSION, "project_id": str(uuid.uuid4()),
        "name": args.name, "idea": args.idea, "created_at": now(), "updated_at": now(),
        "settings": {"goal": args.goal, "aspect_ratio": args.aspect_ratio, "total_seconds": args.total_seconds, "assemble": args.assemble},
        "active_node": "project", "next_action": "确认项目目标，然后发展完整故事与时长。",
        "nodes": {node: {"status": "in_progress" if node == "project" else "not_started", "note": ""} for node in NODES},
        "segments": {}, "assets": {}, "videos": {}, "artifacts": {}, "pending_decisions": [], "risks": [],
    }
    save(root, data, "init")
    return {"ok": True, "project_root": str(root), "plan": str(root / PLAN), "project_id": data["project_id"]}


def cmd_node(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    if args.name == "story" and args.status == "confirmed" and "approved_story" not in data["artifacts"]:
        raise ProjectError("Story confirmation requires an approved story-development checkpoint")
    if args.name == "segments" and args.status == "confirmed" and (not data["segments"] or any(s.get("status") != "confirmed" for s in data["segments"].values())):
        raise ProjectError("Segment confirmation requires confirmed segment records")
    if args.name == "delivery" and args.status == "confirmed":
        errors = completion_errors(data)
        if errors:
            raise ProjectError("Delivery cannot be confirmed: " + "; ".join(errors))
    data["nodes"][args.name] = {"status": args.status, "note": args.note or ""}
    if args.active:
        data["active_node"] = args.name
    if args.next_action:
        data["next_action"] = args.next_action
    save(args.project_dir, data, f"node:{args.name}:{args.status}")
    return {"ok": True, "node": args.name, "status": args.status}


def cmd_record(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    check_id(args.id)
    item = json.loads(args.data_file.read_text(encoding="utf-8"))
    if not isinstance(item, dict) or item.get("status") not in ITEM_STATUSES[args.kind]:
        raise ProjectError(f"Invalid {args.kind} record or status")
    if args.kind == "segment":
        check_segment(item)
    if args.kind == "video":
        segment_id = item.get("segment_id")
        if segment_id not in data["segments"]:
            raise ProjectError(f"Unknown segment: {segment_id}")
        if item["status"] in {"submitted", "processing", "generated", "qa_failed", "accepted"} and not item.get("task_id"):
            raise ProjectError("Submitted video requires task_id")
        if item["status"] in {"submitted", "processing", "generated", "qa_failed", "accepted"} and not item.get("request_hash"):
            raise ProjectError("Submitted video requires request_hash")
        if item["status"] == "accepted" and not item.get("output"):
            raise ProjectError("Accepted video requires output artifact")
        if item["status"] == "accepted" and item.get("qa", {}).get("status") != "pass":
            raise ProjectError("Accepted video requires passing QA")
        if item["status"] in {"accepted", "qa_failed"}:
            check_video_duration(item)
        if item.get("provider_raw") and item.get("provider_raw_sha256"):
            raw = resolve_inside(args.project_dir, item["provider_raw"])
            if not raw.is_file() or digest(raw) != item["provider_raw_sha256"]:
                raise ProjectError("Provider raw video missing or hash mismatch")
    if args.kind == "asset" and item["status"] == "approved" and not item.get("approved_package"):
        raise ProjectError("Approved asset requires approved_package")
    if args.kind == "asset" and item["status"] == "approved":
        package = resolve_inside(args.project_dir, item["approved_package"])
        content = json.loads(package.read_text(encoding="utf-8"))
        matches = [a for a in content.get("assets", []) if a.get("asset_id") == args.id]
        if len(matches) != 1 or matches[0].get("approval", {}).get("status") != "approved":
            raise ProjectError("Asset package does not record user approval")
    for key in ("story_file", "request_file", "approved_package", "input_map", "output"):
        if item.get(key):
            item[key] = artifact(args.project_dir, item[key])
    bucket = data[ITEMS[args.kind]]
    prior = bucket.get(args.id)
    if prior and args.kind == "video" and prior.get("task_id") and item.get("task_id") != prior["task_id"] and int(item.get("version", 0)) <= int(prior.get("version", 1)):
        raise ProjectError("New provider task requires a new video version")
    if prior and prior.get("status") in {"approved", "accepted", "confirmed"} and item != prior:
        if int(item.get("version", 0)) <= int(prior.get("version", 1)):
            raise ProjectError("Revision of accepted item requires a higher version")
        item["history"] = prior.get("history", []) + [{k: v for k, v in prior.items() if k != "history"}]
    item["id"] = args.id
    item.setdefault("version", 1)
    item.pop("review_status", None)
    item["updated_at"] = now()
    bucket[args.id] = item
    save(args.project_dir, data, f"record:{args.kind}:{args.id}:{item['status']}")
    return {"ok": True, "kind": args.kind, "id": args.id, "status": item["status"]}


def cmd_attach(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    data["artifacts"][args.name] = artifact(args.project_dir, args.file)
    save(args.project_dir, data, f"attach:{args.name}")
    return {"ok": True, "name": args.name, **data["artifacts"][args.name]}


def cmd_story(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    path = resolve_inside(args.project_dir, args.file)
    checkpoint = json.loads(path.read_text(encoding="utf-8"))
    review = checkpoint.get("review", {})
    duration = checkpoint.get("duration", {})
    if checkpoint.get("schema") != "story-development" or checkpoint.get("schema_version") != 1 or review.get("status") != "approved" or not review.get("story_sha256"):
        raise ProjectError("Story-development checkpoint is not approved")
    story_text = checkpoint.get("story_text")
    if not story_text:
        raise ProjectError("Approved story text is empty")
    if review["story_sha256"] != hashlib.sha256(story_text.encode("utf-8")).hexdigest():
        raise ProjectError("Approved story hash does not match story_text")
    if duration.get("status") != "approved":
        raise ProjectError("Story duration is not approved")
    target_seconds = duration.get("approved_seconds")
    if type(target_seconds) not in (int, float) or not math.isfinite(target_seconds) or target_seconds <= 0:
        raise ProjectError("Approved story duration.approved_seconds must be a positive number")
    if args.goal is not None and not args.goal.strip():
        raise ProjectError("Project goal must not be empty")
    data["artifacts"]["approved_story"] = {**artifact(args.project_dir, args.file), "story_sha256": review["story_sha256"]}
    data["settings"]["total_seconds"] = target_seconds
    if args.goal is not None:
        data["settings"]["goal"] = args.goal.strip()
    data["nodes"]["story"] = {"status": "confirmed", "note": "完整故事与时长已批准"}
    data["active_node"] = "segments"
    data["next_action"] = "将已批准故事划分为可生成的视频片段并确认片段计划。"
    save(args.project_dir, data, "story:approved")
    return {"ok": True, "artifact_sha256": data["artifacts"]["approved_story"]["sha256"], "story_sha256": review["story_sha256"]}


def cmd_note(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    bucket = data["pending_decisions" if args.kind == "decision" else "risks"]
    if args.remove:
        if args.text not in bucket:
            raise ProjectError("Note not found")
        bucket.remove(args.text)
    elif args.text not in bucket:
        bucket.append(args.text)
    save(args.project_dir, data, f"note:{args.kind}:{'remove' if args.remove else 'add'}")
    return {"ok": True, "kind": args.kind, "count": len(bucket)}


def cmd_impact(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    source = args.source
    affected: list[str] = []
    if source == "story":
        for group in ("segments", "assets", "videos"):
            for key, item in data[group].items():
                item["review_status"] = "needs_review"
                affected.append(f"{group}:{key}")
        for node in NODES[NODES.index("segments"):]:
            if data["nodes"][node]["status"] == "confirmed":
                data["nodes"][node]["status"] = "needs_review"
    elif source.startswith("segment:"):
        segment_id = source.split(":", 1)[1]
        if segment_id not in data["segments"]:
            raise ProjectError(f"Unknown segment: {segment_id}")
        data["segments"][segment_id]["review_status"] = "needs_review"
        affected.append(source)
        for key, item in data["assets"].items():
            if segment_id in item.get("consumers", []):
                item["review_status"] = "needs_review"
                affected.append(f"assets:{key}")
        for key, item in data["videos"].items():
            if item.get("segment_id") == segment_id:
                item["review_status"] = "needs_review"
                affected.append(f"videos:{key}")
        for node in ("prompt-pass-1", "assets", "prompt-pass-2", "video-generation", "video-qa"):
            if data["nodes"][node]["status"] == "confirmed":
                data["nodes"][node]["status"] = "needs_review"
    elif source.startswith("asset:"):
        asset_id = source.split(":", 1)[1]
        if asset_id not in data["assets"]:
            raise ProjectError(f"Unknown asset: {asset_id}")
        data["assets"][asset_id]["review_status"] = "needs_review"
        affected.append(source)
        consumers = set(data["assets"][asset_id].get("consumers", []))
        for segment_id in consumers:
            if segment_id in data["segments"]:
                data["segments"][segment_id]["binding_review_status"] = "needs_review"
                affected.append(f"segments:{segment_id}:bindings")
        for key, item in data["videos"].items():
            if item.get("segment_id") in consumers:
                item["review_status"] = "needs_review"
                affected.append(f"videos:{key}")
        for node in ("prompt-pass-2", "video-generation", "video-qa"):
            if data["nodes"][node]["status"] == "confirmed":
                data["nodes"][node]["status"] = "needs_review"
    else:
        raise ProjectError("Impact source must be story, segment:<id>, or asset:<id>")
    data["active_node"] = "story" if source == "story" else "segments" if source.startswith("segment:") else "assets"
    data["next_action"] = f"复核 {source} 的变更及受影响项：{args.reason}"
    save(args.project_dir, data, f"impact:{source}")
    return {"ok": True, "affected": affected}


def cmd_validate(args: argparse.Namespace) -> dict:
    data = read(args.project_dir)
    errors: list[str] = []
    if not (args.project_dir / PLAN).is_file():
        errors.append("Plan file missing")
    elif (args.project_dir / PLAN).read_text(encoding="utf-8") != render(data):
        errors.append("Plan differs from machine project state")
    for group in ("artifacts", "segments", "assets", "videos"):
        collection = data[group]
        for item_id, item in collection.items():
            records = [item] if group == "artifacts" else [v for v in item.values() if isinstance(v, dict) and "path" in v]
            for record in records:
                try:
                    path = resolve_inside(args.project_dir, record["path"])
                    if not path.is_file() or digest(path) != record["sha256"]:
                        errors.append(f"Missing/changed artifact: {group}:{item_id}:{record['path']}")
                except (KeyError, OSError, ProjectError) as exc:
                    errors.append(str(exc))
    for video_id, video in data["videos"].items():
        if video.get("segment_id") not in data["segments"]:
            errors.append(f"Video {video_id} has unknown segment")
        if video["status"] in {"submitted", "processing", "generated", "qa_failed", "accepted"} and not video.get("task_id"):
            errors.append(f"Video {video_id} missing task_id")
        try:
            if video["status"] in {"accepted", "qa_failed"}:
                check_video_duration(video)
            if video.get("provider_raw") and video.get("provider_raw_sha256"):
                raw = resolve_inside(args.project_dir, video["provider_raw"])
                if not raw.is_file() or digest(raw) != video["provider_raw_sha256"]:
                    errors.append(f"Video {video_id} provider raw video missing or hash mismatch")
        except (OSError, ProjectError) as exc:
            errors.append(f"Video {video_id}: {exc}")
    for segment_id, segment in data["segments"].items():
        try:
            check_segment(segment)
        except ProjectError as exc:
            errors.append(f"Segment {segment_id}: {exc}")
    if args.require_complete or data["nodes"]["delivery"]["status"] == "confirmed":
        errors.extend(completion_errors(data))
    return {"ok": not errors, "errors": errors, "project_root": str(args.project_dir), "segments": len(data["segments"]), "assets": len(data["assets"]), "videos": len(data["videos"])}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project-dir", type=Path, required=True)
    init.add_argument("--name", required=True)
    init.add_argument("--idea", required=True)
    init.add_argument("--goal", default="生成并验收全部规划视频片段")
    init.add_argument("--aspect-ratio", default="待定")
    init.add_argument("--total-seconds", type=float)
    init.add_argument("--assemble", action="store_true")
    for name in ("status", "validate"):
        q = sub.add_parser(name)
        q.add_argument("--project-dir", type=Path, required=True)
        if name == "validate":
            q.add_argument("--require-complete", action="store_true")
    node = sub.add_parser("node")
    node.add_argument("--project-dir", type=Path, required=True)
    node.add_argument("--name", choices=NODES, required=True)
    node.add_argument("--status", choices=sorted(STATUSES), required=True)
    node.add_argument("--note")
    node.add_argument("--next-action")
    node.add_argument("--active", action="store_true")
    record = sub.add_parser("record")
    record.add_argument("--project-dir", type=Path, required=True)
    record.add_argument("--kind", choices=sorted(ITEMS), required=True)
    record.add_argument("--id", required=True)
    record.add_argument("--data-file", type=Path, required=True)
    attach = sub.add_parser("attach")
    attach.add_argument("--project-dir", type=Path, required=True)
    attach.add_argument("--name", required=True)
    attach.add_argument("--file", required=True)
    story = sub.add_parser("story")
    story.add_argument("--project-dir", type=Path, required=True)
    story.add_argument("--file", required=True, help="Project-relative approved story-development.json")
    story.add_argument("--goal", help="Updated human-readable project goal when the approved story replaces the initial estimate")
    note = sub.add_parser("note")
    note.add_argument("--project-dir", type=Path, required=True)
    note.add_argument("--kind", choices=["decision", "risk"], required=True)
    note.add_argument("--text", required=True)
    note.add_argument("--remove", action="store_true")
    impact = sub.add_parser("impact")
    impact.add_argument("--project-dir", type=Path, required=True)
    impact.add_argument("--source", required=True)
    impact.add_argument("--reason", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command != "init":
        args.project_dir = args.project_dir.expanduser().resolve()
    try:
        if args.command == "init":
            result = cmd_init(args)
        elif args.command == "status":
            data = read(args.project_dir)
            result = {"ok": True, "active_node": data["active_node"], "next_action": data["next_action"], "plan": str(args.project_dir / PLAN), "segments": len(data["segments"]), "assets": len(data["assets"]), "videos": len(data["videos"])}
        elif args.command == "node":
            result = cmd_node(args)
        elif args.command == "record":
            result = cmd_record(args)
        elif args.command == "attach":
            result = cmd_attach(args)
        elif args.command == "story":
            result = cmd_story(args)
        elif args.command == "note":
            result = cmd_note(args)
        elif args.command == "impact":
            result = cmd_impact(args)
        else:
            result = cmd_validate(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2
    except (ProjectError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
