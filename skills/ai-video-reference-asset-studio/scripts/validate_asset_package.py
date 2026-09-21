#!/usr/bin/env python3
"""Validate an ai-video-reference-asset-package JSON file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


TOP_REQUIRED = {"schema", "schema_version", "status", "project", "source", "assets", "unresolved_assets"}
ASSET_REQUIRED = {
    "asset_id", "source_task_id", "kind", "name", "purpose", "consumers", "definition_scope",
    "dependencies", "identity_root", "references", "operator_notes", "prompt_text",
    "interface_parameters", "acceptance_checks", "attempts", "qa", "approval", "status", "output",
}
CURRENT_ASSET_REQUIRED = {"asset_form"}
KINDS = {"character", "environment", "prop", "style", "keyframe"}
PACKAGE_STATUSES = {"planned", "partial", "complete"}
ASSET_STATUSES = {"planned", "blocked", "candidate-generated", "technical-pass", "approved", "rejected"}
ASSET_FORMS = {"higgsfield-three-panel", "single-identity-seed", "derived-character-control", "character-identity-root", "environment-reference", "prop-reference", "multi-state-prop-board", "style-reference", "style-reference-frame", "multi-panel-style-board", "shot-keyframe"}
HIGGSFIELD_PANEL_ROLES_V1_1 = ["front-full-body", "back-full-body", "frontal-close-up"]
HIGGSFIELD_PANEL_ROLES_V1_2 = ["front-full-body-face-removed", "back-full-body-no-face", "frontal-close-up-face-authority"]
TECHNICAL_RESULTS = {"not-run", "pass", "fail", "needs-review"}
APPROVAL_STATUSES = {"pending", "approved", "rejected"}
DEP_STRENGTHS = {"hard", "advisory", "unresolved"}
REF_BINDINGS = {"identity", "structure", "geometry", "style", "state", "scale", "composition", "other"}
STYLE_CONTROLS = {"photographic_register", "lighting", "palette", "materials", "contrast", "texture"}
STYLE_PROMPT_FORMATS = {"fixed-style-prompt"}


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def result_path(attempt: dict) -> str | None:
    result = attempt.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        value = result.get("path") or result.get("artifact")
        return value if isinstance(value, str) else None
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_ratio(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", value)
    if not match:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        return None
    return width / height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with args.package.open("r", encoding="utf-8") as handle:
            package = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [f"cannot read package: {exc}"], "warnings": []}, ensure_ascii=False, indent=2))
        return 1
    add(errors, isinstance(package, dict), "package root must be an object")
    if not isinstance(package, dict):
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 1
    for key in sorted(TOP_REQUIRED):
        add(errors, key in package, f"missing top-level field: {key}")
    add(errors, package.get("schema") == "ai-video-reference-asset-package", "schema must be ai-video-reference-asset-package")
    schema_version = package.get("schema_version")
    add(errors, schema_version in {"1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0"}, "schema_version must be 1.0.0 through 1.4.0")
    add(errors, package.get("status") in PACKAGE_STATUSES, "invalid package status")
    assets = package.get("assets")
    add(errors, isinstance(assets, list), "assets must be an array")
    if not isinstance(assets, list):
        assets = []
    seen: set[str] = set()
    approved_count = 0
    base_dir = args.package.parent
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in sorted(ASSET_REQUIRED):
            add(errors, key in asset, f"{prefix} missing field: {key}")
        if schema_version in {"1.1.0", "1.2.0", "1.3.0", "1.4.0"}:
            for key in sorted(CURRENT_ASSET_REQUIRED):
                add(errors, key in asset, f"{prefix} missing current field: {key}")
            add(errors, asset.get("asset_form") in ASSET_FORMS, f"{prefix}.asset_form is invalid")
        asset_id = asset.get("asset_id")
        add(errors, isinstance(asset_id, str) and bool(asset_id.strip()), f"{prefix}.asset_id must be non-empty")
        if isinstance(asset_id, str):
            add(errors, asset_id not in seen, f"duplicate asset_id: {asset_id}")
            seen.add(asset_id)
        add(errors, asset.get("kind") in KINDS, f"{prefix}.kind is invalid")
        source_task_id = asset.get("source_task_id")
        if isinstance(asset_id, str) and isinstance(source_task_id, str) and asset_id != source_task_id:
            source_name = asset.get("source_name")
            add(errors, isinstance(source_name, str) and bool(source_name.strip()), f"{prefix}.source_name is required for a compound child")
            add(errors, isinstance(asset.get("name"), str) and asset.get("name", "").startswith(f"{source_name or ''}·"), f"{prefix}.name must use parent-name middle-dot child-label")
            variant = asset.get("variant")
            add(errors, isinstance(variant, dict), f"{prefix}.variant must be an object for a compound child")
            if isinstance(variant, dict):
                add(errors, isinstance(variant.get("type"), str) and bool(variant.get("type", "").strip()), f"{prefix}.variant.type is required")
                add(errors, isinstance(variant.get("value"), str) and bool(variant.get("value", "").strip()), f"{prefix}.variant.value is required")
        add(errors, asset.get("status") in ASSET_STATUSES, f"{prefix}.status is invalid")
        if asset.get("asset_form") == "higgsfield-three-panel":
            panel_spec = asset.get("panel_spec")
            add(errors, isinstance(panel_spec, list), f"{prefix}.panel_spec must be an array")
            roles = [panel.get("role") for panel in panel_spec if isinstance(panel, dict)] if isinstance(panel_spec, list) else []
            expected_roles = HIGGSFIELD_PANEL_ROLES_V1_2 if schema_version in {"1.2.0", "1.3.0", "1.4.0"} else HIGGSFIELD_PANEL_ROLES_V1_1
            add(errors, roles == expected_roles, f"{prefix}.panel_spec roles must be {expected_roles}")
            parameters = asset.get("interface_parameters")
            add(errors, isinstance(parameters, dict) and parameters.get("aspect_ratio") == "16:9", f"{prefix} Higgsfield sheet must declare 16:9 aspect_ratio")
            if schema_version in {"1.2.0", "1.3.0", "1.4.0"}:
                face_authority = asset.get("face_authority")
                add(errors, isinstance(face_authority, dict), f"{prefix}.face_authority must be an object")
                if isinstance(face_authority, dict):
                    add(errors, face_authority.get("exclusive_panel") == "frontal-close-up-face-authority", f"{prefix}.face_authority.exclusive_panel is invalid")
                    add(errors, face_authority.get("other_panels_must_not_show_face") is True, f"{prefix}.face_authority must forbid faces in other panels")
        if asset.get("asset_form") == "multi-state-prop-board":
            panel_spec = asset.get("panel_spec")
            add(errors, isinstance(panel_spec, list) and len(panel_spec) >= 2, f"{prefix}.panel_spec must contain at least two panels")
            roles: list[str] = []
            for panel_index, panel in enumerate(panel_spec if isinstance(panel_spec, list) else []):
                pp = f"{prefix}.panel_spec[{panel_index}]"
                add(errors, isinstance(panel, dict), f"{pp} must be an object")
                if not isinstance(panel, dict):
                    continue
                for key in ("panel_id", "role", "purpose", "authority", "crop_box_normalized", "crop_path", "crop_pixels", "crop_sha256"):
                    add(errors, key in panel, f"{pp} missing field: {key}")
                role = panel.get("role")
                add(errors, isinstance(role, str) and bool(role.strip()), f"{pp}.role must be non-empty")
                if isinstance(role, str):
                    roles.append(role)
                add(errors, isinstance(panel.get("authority"), list) and bool(panel.get("authority")), f"{pp}.authority must be a non-empty array")
                box = panel.get("crop_box_normalized")
                add(errors, isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box), f"{pp}.crop_box_normalized must be four numbers")
                if isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
                    add(errors, 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1, f"{pp}.crop_box_normalized must satisfy 0<=left<right<=1 and 0<=top<bottom<=1")
                crop_path_value = panel.get("crop_path")
                add(errors, isinstance(crop_path_value, str) and crop_path_value.startswith("intermediate/panel-crops/"), f"{pp}.crop_path must be under intermediate/panel-crops/")
                if args.check_files and isinstance(crop_path_value, str):
                    crop_path = base_dir / crop_path_value
                    add(errors, crop_path.is_file(), f"{pp}.crop_path does not exist: {crop_path_value}")
                    if crop_path.is_file():
                        add(errors, sha256_file(crop_path) == panel.get("crop_sha256"), f"{pp}.crop_sha256 mismatch")
            add(errors, len(roles) == len(set(roles)), f"{prefix}.panel_spec roles must be unique")
        if asset.get("asset_form") == "single-identity-seed":
            add(errors, asset.get("status") != "approved", f"{prefix} single-identity-seed cannot be an approved production asset")
        if asset.get("asset_form") == "derived-character-control":
            operator_notes = asset.get("operator_notes")
            control_type = operator_notes.get("control_type") if isinstance(operator_notes, dict) else None
            if control_type is not None:
                add(errors, control_type in {"angle", "state", "other"}, f"{prefix}.operator_notes.control_type is invalid")
            if control_type == "state":
                parameters = asset.get("interface_parameters")
                add(errors, isinstance(parameters, dict) and parameters.get("aspect_ratio") == "9:16", f"{prefix} character state must declare 9:16 aspect_ratio")
                prompt_text = asset.get("prompt_text")
                add(errors, isinstance(prompt_text, str) and "9:16" in prompt_text, f"{prefix} character state prompt must declare 9:16 composition")
            identity_root = asset.get("identity_root")
            add(errors, isinstance(identity_root, dict), f"{prefix}.identity_root must be an object")
            root_path_value = None
            if isinstance(identity_root, dict):
                add(errors, identity_root.get("type") == "approved-base-reference", f"{prefix}.identity_root.type must be approved-base-reference")
                for key in ("root_task_id", "path", "sha256", "package_path"):
                    add(errors, isinstance(identity_root.get(key), str) and bool(identity_root.get(key, "").strip()), f"{prefix}.identity_root.{key} is required")
                add(errors, identity_root.get("approved") is True, f"{prefix}.identity_root.approved must be true")
                add(errors, identity_root.get("root_task_id") != asset.get("source_task_id"), f"{prefix}.identity_root must identify an earlier root task")
                root_path_value = identity_root.get("path")
                if isinstance(root_path_value, str):
                    add(errors, not Path(root_path_value).is_absolute(), f"{prefix}.identity_root.path must be relative to the package")
                package_path_value = identity_root.get("package_path")
                if isinstance(package_path_value, str):
                    add(errors, not Path(package_path_value).is_absolute(), f"{prefix}.identity_root.package_path must be relative to the package")
                if args.check_files and isinstance(root_path_value, str) and root_path_value:
                    root_path = Path(root_path_value)
                    root_path = base_dir / root_path
                    add(errors, root_path.is_file(), f"{prefix}.identity_root.path does not exist: {root_path_value}")
                    if root_path.is_file():
                        add(errors, sha256_file(root_path) == identity_root.get("sha256"), f"{prefix}.identity_root.sha256 mismatch")
                if args.check_files and isinstance(package_path_value, str) and package_path_value:
                    add(errors, (base_dir / package_path_value).is_file(), f"{prefix}.identity_root.package_path does not exist: {package_path_value}")
        if asset.get("asset_form") in {"style-reference-frame", "multi-panel-style-board"}:
            style_authority = asset.get("style_authority")
            add(errors, isinstance(style_authority, dict), f"{prefix}.style_authority must be an object")
            if isinstance(style_authority, dict):
                controls = style_authority.get("controls")
                add(errors, isinstance(controls, list) and bool(controls), f"{prefix}.style_authority.controls must be a non-empty array")
                if isinstance(controls, list):
                    add(errors, set(controls) <= STYLE_CONTROLS, f"{prefix}.style_authority.controls contains an invalid value")
                    add(errors, len(controls) == len(set(controls)), f"{prefix}.style_authority.controls contains duplicates")
                add(errors, style_authority.get("identity_authority") is False, f"{prefix}.style_authority.identity_authority must be false")
                add(errors, style_authority.get("geometry_authority") is False, f"{prefix}.style_authority.geometry_authority must be false")
            parameters = asset.get("interface_parameters")
            add(errors, isinstance(parameters, dict) and bool(parameters.get("aspect_ratio")), f"{prefix} style asset must declare aspect_ratio")
        if asset.get("asset_form") == "multi-panel-style-board":
            board = asset.get("style_board")
            add(errors, isinstance(board, dict), f"{prefix}.style_board must be an object")
            if isinstance(board, dict):
                add(errors, board.get("format") == "multi-panel-style-board", f"{prefix}.style_board.format must be multi-panel-style-board")
                add(errors, bool(board.get("layout")), f"{prefix}.style_board.layout is required")
                panels = board.get("scene_panels")
                add(errors, isinstance(panels, list) and len(panels) >= 2, f"{prefix}.style_board.scene_panels must contain at least two panels")
                palette = board.get("palette")
                add(errors, isinstance(palette, dict) and bool(palette), f"{prefix}.style_board.palette must be a non-empty object")
                samples = board.get("material_samples")
                add(errors, isinstance(samples, list) and bool(samples), f"{prefix}.style_board.material_samples must be a non-empty array")
        if asset.get("asset_form") == "shot-keyframe":
            add(errors, asset.get("kind") == "keyframe", f"{prefix} shot-keyframe must use kind keyframe")
            composition = asset.get("composition_control")
            add(errors, isinstance(composition, dict), f"{prefix}.composition_control must be an object")
            composition_path_value = None
            if isinstance(composition, dict):
                for key in ("task_id", "path", "sha256", "authority", "excluded_properties"):
                    add(errors, key in composition, f"{prefix}.composition_control.{key} is required")
                add(errors, composition.get("authority") == "composition-only", f"{prefix}.composition_control.authority must be composition-only")
                add(errors, isinstance(composition.get("excluded_properties"), list) and bool(composition.get("excluded_properties")), f"{prefix}.composition_control.excluded_properties must be a non-empty array")
                composition_path_value = composition.get("path")
                if isinstance(composition_path_value, str):
                    add(errors, not Path(composition_path_value).is_absolute(), f"{prefix}.composition_control.path must be relative to the package")
                    if args.check_files:
                        composition_path = base_dir / composition_path_value
                        add(errors, composition_path.is_file(), f"{prefix}.composition_control.path does not exist: {composition_path_value}")
                        if composition_path.is_file():
                            add(errors, sha256_file(composition_path) == composition.get("sha256"), f"{prefix}.composition_control.sha256 mismatch")
            parameters = asset.get("interface_parameters")
            add(errors, isinstance(parameters, dict) and bool(parameters.get("aspect_ratio")), f"{prefix} shot-keyframe must declare aspect_ratio")
            operator_notes = asset.get("operator_notes")
            add(errors, isinstance(operator_notes, dict) and bool(operator_notes.get("keyframe_role")), f"{prefix}.operator_notes.keyframe_role is required")
            add(errors, isinstance(operator_notes, dict) and bool(operator_notes.get("prompt_translation_zh")), f"{prefix}.operator_notes.prompt_translation_zh is required")
        style_controls = asset.get("style_controls")
        if style_controls is not None:
            add(errors, asset.get("kind") in {"environment", "keyframe"}, f"{prefix}.style_controls is only valid for environment assets or keyframes")
            add(errors, isinstance(style_controls, list) and bool(style_controls), f"{prefix}.style_controls must be a non-empty array")
            for control_index, control in enumerate(style_controls if isinstance(style_controls, list) else []):
                cp = f"{prefix}.style_controls[{control_index}]"
                add(errors, isinstance(control, dict), f"{cp} must be an object")
                if not isinstance(control, dict):
                    continue
                add(errors, bool(control.get("source_task_id")), f"{cp}.source_task_id is required")
                add(errors, control.get("format") in STYLE_PROMPT_FORMATS, f"{cp}.format is invalid")
                add(errors, isinstance(control.get("prompt_core"), str) and bool(control.get("prompt_core", "").strip()), f"{cp}.prompt_core is required")
                override = control.get("scene_override")
                add(errors, isinstance(override, dict), f"{cp}.scene_override must be an object")
                if isinstance(override, dict):
                    expected_override_ids = {asset.get("source_task_id")}
                    if asset.get("kind") == "keyframe" and isinstance(asset.get("operator_notes"), dict):
                        expected_override_ids.update(asset["operator_notes"].get("environment_task_ids", []))
                    add(errors, override.get("task_id") in expected_override_ids, f"{cp}.scene_override.task_id must match the asset or keyframe environment task")
                    add(errors, isinstance(override.get("prompt"), str) and bool(override.get("prompt", "").strip()), f"{cp}.scene_override.prompt is required")
                authority = control.get("authority")
                add(errors, isinstance(authority, dict), f"{cp}.authority must be an object")
                if isinstance(authority, dict):
                    for key in STYLE_CONTROLS:
                        add(errors, authority.get(key) is True, f"{cp}.authority.{key} must be true")
                    add(errors, authority.get("exact_geometry") is False, f"{cp}.authority.exact_geometry must be false")
                    add(errors, authority.get("character_identity") is False, f"{cp}.authority.character_identity must be false")
        dependencies = asset.get("dependencies")
        add(errors, isinstance(dependencies, list), f"{prefix}.dependencies must be an array")
        for dep_index, dependency in enumerate(dependencies if isinstance(dependencies, list) else []):
            dp = f"{prefix}.dependencies[{dep_index}]"
            add(errors, isinstance(dependency, dict), f"{dp} must be an object")
            if isinstance(dependency, dict):
                add(errors, dependency.get("strength") in DEP_STRENGTHS, f"{dp}.strength is invalid")
                add(errors, bool(dependency.get("asset_id")), f"{dp}.asset_id is required")
        references = asset.get("references")
        add(errors, isinstance(references, list), f"{prefix}.references must be an array")
        for ref_index, reference in enumerate(references if isinstance(references, list) else []):
            rp = f"{prefix}.references[{ref_index}]"
            add(errors, isinstance(reference, dict), f"{rp} must be an object")
            if isinstance(reference, dict):
                for key in ("reference_id", "role", "binding", "status"):
                    add(errors, key in reference, f"{rp}.{key} is required")
                add(errors, reference.get("binding") in REF_BINDINGS, f"{rp}.binding is invalid")
        if asset.get("asset_form") == "derived-character-control" and isinstance(root_path_value, str):
            matching_root_refs = [
                reference for reference in references if isinstance(reference, dict)
                and reference.get("role") == "identity"
                and reference.get("binding") == "identity"
                and reference.get("path") == root_path_value
            ] if isinstance(references, list) else []
            add(errors, len(matching_root_refs) == 1, f"{prefix} must contain one identity reference matching identity_root.path")
        if asset.get("asset_form") == "shot-keyframe" and isinstance(composition_path_value, str):
            matching_composition_refs = [
                reference for reference in references if isinstance(reference, dict)
                and reference.get("role") == "composition"
                and reference.get("binding") == "composition"
                and reference.get("path") == composition_path_value
            ] if isinstance(references, list) else []
            add(errors, len(matching_composition_refs) == 1, f"{prefix} must contain one composition reference matching composition_control.path")
        attempts = asset.get("attempts")
        add(errors, isinstance(attempts, list), f"{prefix}.attempts must be an array")
        selected = [attempt for attempt in attempts if isinstance(attempt, dict) and attempt.get("selected") is True] if isinstance(attempts, list) else []
        add(errors, len(selected) <= 1, f"{prefix} has more than one selected attempt")
        for attempt_index, attempt in enumerate(attempts if isinstance(attempts, list) else []):
            ap = f"{prefix}.attempts[{attempt_index}]"
            add(errors, isinstance(attempt, dict), f"{ap} must be an object")
            if not isinstance(attempt, dict):
                continue
            for key in ("prompt", "input_files", "provider", "parameters", "result", "selected", "reason"):
                add(errors, key in attempt, f"{ap}.{key} is required")
            if asset.get("asset_form") == "derived-character-control" and isinstance(root_path_value, str):
                add(errors, isinstance(attempt.get("input_files"), list) and root_path_value in attempt.get("input_files", []), f"{ap}.input_files must include identity_root.path")
            if asset.get("asset_form") == "shot-keyframe" and isinstance(composition_path_value, str):
                files = attempt.get("input_files")
                add(errors, isinstance(files, list) and bool(files) and files[0] == composition_path_value, f"{ap}.input_files must place composition_control.path first")
                add(errors, attempt.get("prompt") == asset.get("prompt_text"), f"{ap}.prompt must exactly equal the submitted keyframe prompt_text")
            operator_notes = asset.get("operator_notes")
            control_type = operator_notes.get("control_type") if isinstance(operator_notes, dict) else None
            if asset.get("asset_form") == "derived-character-control" and control_type == "state" and attempt.get("selected") is True:
                attempt_parameters = attempt.get("parameters")
                add(errors, isinstance(attempt_parameters, dict) and attempt_parameters.get("requested_aspect_ratio") == "9:16", f"{ap}.parameters.requested_aspect_ratio must be 9:16 for a character state")
                returned_ratio = pixel_ratio(attempt_parameters.get("returned_pixels")) if isinstance(attempt_parameters, dict) else None
                add(errors, returned_ratio is not None, f"{ap}.parameters.returned_pixels must record the generated character-state canvas")
                if returned_ratio is not None:
                    add(errors, abs(returned_ratio - (9 / 16)) <= 0.02, f"{ap}.parameters.returned_pixels must be approximately 9:16 for a character state")
            path_value = result_path(attempt)
            if args.check_files and path_value:
                artifact = Path(path_value)
                if not artifact.is_absolute():
                    artifact = base_dir / artifact
                add(errors, artifact.is_file(), f"{ap} result file does not exist: {path_value}")
        qa = asset.get("qa")
        add(errors, isinstance(qa, dict), f"{prefix}.qa must be an object")
        if isinstance(qa, dict):
            add(errors, qa.get("technical_result") in TECHNICAL_RESULTS, f"{prefix}.qa.technical_result is invalid")
            for key in ("visible_observations", "inspector", "date"):
                add(errors, key in qa, f"{prefix}.qa.{key} is required")
        approval = asset.get("approval")
        add(errors, isinstance(approval, dict), f"{prefix}.approval must be an object")
        if isinstance(approval, dict):
            add(errors, approval.get("status") in APPROVAL_STATUSES, f"{prefix}.approval.status is invalid")
            for key in ("actor", "date", "note"):
                add(errors, key in approval, f"{prefix}.approval.{key} is required")
        if asset.get("status") == "approved":
            approved_count += 1
            add(errors, len(selected) == 1, f"{prefix} approved asset must have one selected attempt")
            add(errors, isinstance(qa, dict) and qa.get("technical_result") == "pass", f"{prefix} approved asset must pass technical QA")
            add(errors, isinstance(approval, dict) and approval.get("status") == "approved", f"{prefix} approved asset must have user approval")
            add(errors, bool(asset.get("output")), f"{prefix} approved asset must have output")
        elif isinstance(approval, dict) and approval.get("status") == "approved":
            errors.append(f"{prefix} user approval cannot be approved while asset status is {asset.get('status')!r}")
    if package.get("status") == "complete":
        add(errors, len(assets) > 0 and approved_count == len(assets), "complete package requires every asset to be approved")
        add(errors, package.get("unresolved_assets") == [], "complete package cannot have unresolved_assets")
    if not assets:
        warnings.append("package contains no assets")
    report = {"ok": not errors, "errors": errors, "warnings": warnings, "asset_count": len(assets), "approved_count": approved_count}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
