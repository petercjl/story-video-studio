# story-video-studio

Cross-Agent story-video production workflow for Codex and SealSeek. The npm
package is the canonical distribution for the managed Skill suite and its
update, installation, dependency, and diagnostic commands.

## Install

```bash
npm install --global @petercjl/story-video-studio
story-video-studio skill install --agent sealseek
story-video-studio doctor --agent sealseek --json
```

Use `--agent codex` for Codex or `--agent all` for both managed targets.
SealSeek on Windows receives managed copies. Platforms that support directory
links use links by default.

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
