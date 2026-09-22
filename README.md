# story-video-studio

Cross-Agent story-video production workflow for Codex and SealSeek. The npm
package is the canonical distribution for the managed Skill suite and its
update, installation, dependency, and diagnostic commands.

## Install

```bash
npm install --global @petercjl/story-video-studio
story-video-studio setup --agent sealseek --json
story-video-studio doctor --agent sealseek --json
```

Use `--agent codex` for Codex or `--agent all` for both managed targets.
SealSeek on Windows receives managed copies. Platforms that support directory
links use links by default.

`setup` is safe to run again. A current managed installation returns
`unchanged: true`. Windows Skill copies update inside their existing directory,
which avoids replacing a live directory that SealSeek is reading.

## Runtime and workflow checks

The package uses the active Node runtime, discovers SealSeek's managed Python
on Windows, and includes portable `ffmpeg` and `ffprobe` binaries. A user may
override discovery with `STORY_VIDEO_PYTHON`, `STORY_VIDEO_FFMPEG`, or
`STORY_VIDEO_FFPROBE`.

Run preflight for the node that is about to execute:

```bash
story-video-studio preflight --agent sealseek --node story --json
story-video-studio preflight --agent sealseek --node video-generation --json
story-video-studio preflight --agent sealseek --node delivery --json
```

The supported nodes are `project`, `story`, `segments`, `prompt-pass-1`,
`assets`, `prompt-pass-2`, `video-generation`, `video-qa`, and `delivery`.
`doctor` reports separate suite, story, generation, media, assembly, and
delivery readiness instead of treating every optional production capability as
an installation failure.

Bundled Python utilities run through the portable launcher:

```bash
story-video-studio run-script story-development-director story_checkpoint.py validate path/to/story-development.json
```

## Automatic updates

Every functional CLI command performs a throttled npm registry check. The
default interval is six hours. When a newer release exists, the CLI updates the
global package, refreshes every previously installed managed Skill, validates
the suite, and reexecutes the original command once.

```bash
story-video-studio settings show --json
story-video-studio settings set auto-update on
story-video-studio settings set update-check-hours 6
story-video-studio update --agent sealseek --json
```

Registry lookup failures leave the current verified version usable. A confirmed
new version that cannot be installed or validated returns a structured failure.

## Bundled Skills and external tools

The public package bundles the complete portable Skill suite, including its own
story-development Skill. Media providers remain external capabilities selected
through the Codex or SealSeek runtime adapters.

Credentials, API keys, provider accounts, and Agent configuration remain on the
user's machine. This package contains no service credentials.
