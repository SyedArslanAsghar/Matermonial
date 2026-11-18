# Backend dependencies (pip-tools)

Dependencies are locked with **pip-tools** (owner decision D4, 2026-11-17).

| Input (edit these) | Lockfile (generated; don't edit by hand) | Contents |
|---|---|---|
| `base.in` | `base.txt` | Runtime dependencies |
| `local.in` | `local.txt` | `base.in` + development and test tools (including pip-tools) |
| `production.in` | `production.txt` | `base.in` + the production server |

- Lockfiles pin every package, including transitive ones, with `--generate-hashes`, so `pip install -r` verifies every download.
- `local.in` and `production.in` are constrained by `base.txt` (`-c base.txt`). That way development and production resolve **identical** runtime versions.
- **Supported Python: 3.12 and 3.13** (owner decision DR-2026-11-17-G3C-2; `requires-python = ">=3.12,<3.14"` in `backend/pyproject.toml`). The same lockfiles install, hash-checked, on both versions, and CI tests both.
- Lockfiles are **compiled with Python 3.12**, the minimum supported version. pip-compile resolves for the interpreter it runs on, so compiling on 3.12 deliberately includes the packages that only older Python versions need. For example, `typing-extensions` is required by `psycopg` and `referencing` on Python < 3.13. Those packages are harmless on 3.13. Compiling on 3.13 would drop them and break 3.12 installs.

## Install

```bash
cd backend
source .venv/bin/activate
pip install -r requirements/local.txt     # development
pip check
```

## Add, change or update a dependency

1. Edit the right `.in` file. Keep existing version ranges unless the change is intended, and don't add unrelated packages.
2. Regenerate the lockfiles **with Python 3.12**, from the `backend/` directory (the `# via` annotations record paths relative to it), always in this order (`base` first, because the others are constrained by it):

   ```bash
   cd backend          # in an environment running Python 3.12 with requirements/local.txt installed
   for r in base local production; do
     pip-compile --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url \
       --output-file=requirements/$r.txt requirements/$r.in
   done
   ```

   - To upgrade **one** package within its range, add `--upgrade-package <name>`.
   - To refresh **everything**, add `--upgrade`.
   - Without these flags, existing pins are kept.
3. Reinstall (`pip install -r requirements/local.txt`), run `pip check`, and run the tests, on both Python 3.12 and 3.13.
4. Commit the `.in` and `.txt` changes together. CI recompiles from the committed lockfiles and fails if a lockfile no longer matches its input.
