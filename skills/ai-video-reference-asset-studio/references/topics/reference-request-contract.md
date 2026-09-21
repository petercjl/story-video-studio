# Shot-derived reference request

`ai-video-reference-asset-request@1.x` lists image needs inferred by the video prompt designer from an approved story segment's actual shots. `assets[]` gives stable ID, exact name, kind, intended form, purpose, production brief, consumer shot IDs, dependencies and acceptance checks. The asset studio makes the requested images, checks them, records packages and approvals, and returns paths; it does not redesign the upstream story or infer requirements from a different production table.

`scripts/extract_reference_request.py` accepts the JSON directly, verifies source hashes and exact IDs/names, and emits an `ai-video-reference-asset-work-order@1.0.0`. Selection is an invocation option: `--all`, repeated `--asset-id`, or repeated exact `--asset-name`. Unknown or ambiguous selections fail. Preserve the request file unchanged. The extractor also reads the original 0.1 prototype used during the initial full-chain run.

For a project, write each selected asset into a versioned package under the project's asset root. An approved package remains the authority for downstream use. Record master-board crops in `panel_spec` with role, path and hash. A separate project controller may maintain a project-wide effective-asset registry; the asset studio exposes only approved package paths and does not write the upstream request.
