# Backend dependencies (pip-tools)

Dependencies are locked with **pip-tools** (owner decision D4, 2026-11-17).

| Input (edit these) | Lockfile (generated; don't edit by hand) | Contents |
|---|---|---|
| `base.in` | `base.txt` | Runtime dependencies |
| `local.in` | `local.txt` | `base.in` + development and test tools (including pip-tools) |
| `production.in` | `production.txt` | `base.in` + the production server |

- Lockfiles pin every package, including transitive ones, with `--generate-hashes`, so `pip install -r` verifies every download.
- `local.in` and `production.in` are constrained by `base.txt` (`-c base.txt`). That way development and production resolve **identical** runtime versions.
- Lockfiles are compiled for **Python 3.13**, the version CI uses. Some dependencies add packages only on older Python versions (for example `typing-extensions` on Python < 3.13), so hash-checked installs from these lockfiles need Python 3.13.

## Install

```bash
cd backend
source .venv/bin/activate
pip install -r requirements/local.txt     # development
pip check
```

## Add, change or update a dependency

1. Edit the right `.in` file. Keep existing version ranges unless the change is intended, and don't add unrelated packages.
2. Regenerate the lockfiles, always in this order (`base` first, because the others are constrained by it):

   ```bash
   cd backend
   for r in base local production; do
     pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url \
       --output-file=requirements/$r.txt requirements/$r.in
   done
   ```

   - To upgrade **one** package within its range, add `--upgrade-package <name>`.
   - To refresh **everything**, add `--upgrade`.
   - Without these flags, existing pins are kept.
3. Reinstall (`pip install -r requirements/local.txt`), run `pip check`, and run the tests.
4. Commit the `.in` and `.txt` changes together. CI recompiles from the committed lockfiles and fails if a lockfile no longer matches its input.
