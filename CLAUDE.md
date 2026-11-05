# KDE for Home Assistant

## Branches and releases

- All work happens on the `beta` branch, and every push goes to `beta`.
- Merge or push to `main` only when Quinten says so explicitly in that conversation. Approval for one push does not carry over to the next one.
- A release from `beta` is a GitHub **pre-release** whose tag matches `manifest.json` (for example `v1.1.0b1` for version `1.1.0b1`). HACS only offers it to people who turned on the *Pre-release* switch of this repository, so Quinten can test it in their own Home Assistant first.
- A normal release (`vX.Y.Z`, no `b`) is made from `main`, after the merge Quinten asked for.

## Commits

- Commit as Radeaus `<99103370+Radeaus@users.noreply.github.com>` (repo-local git config).
- Add no `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" line.

## Tests

- Run `.venv/bin/pytest` before every commit.
