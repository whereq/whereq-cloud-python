# Releasing `whereq.cloud` (Python → PyPI)

Publishing is automated: **push a version tag `vX.Y.Z` and GitHub Actions publishes to PyPI
via Trusted Publishing (OIDC).** No tokens are stored anywhere.

## Release a new version (the recurring steps)

Use the script — it does all of the below and refuses to push a half-finished release:

```bash
./release.sh 0.6.1 "the geography endpoints"    # explicit version
./release.sh patch                              # or let it compute the bump
./release.sh minor --dry-run                    # preview: checks + tests, pushes nothing
```

`release.sh` bumps the version in **both** `pyproject.toml` and
`src/whereq_cloud/client.py`, runs the tests, commits, pushes `main`, pushes the tag,
watches the Release workflow and verifies the version on PyPI. It stops before touching
anything remote if any precondition fails.

If you'd rather do it by hand, the steps are:

1. **Bump the version** in `pyproject.toml` → `[project] version = "X.Y.Z"`.
   (Keep it in sync with the tag you'll push — the tag is `v` + this version.)
2. **Update the code / README** as needed; make sure tests pass locally:
   ```bash
   pip install -e . pytest && python -m pytest -q
   ```
3. **Commit to `main`** and push:
   ```bash
   git add -A && git commit -m "release: vX.Y.Z" && git push origin main
   ```
   (Pushing to `main` only runs CI — it does **not** publish.)
4. **Tag and push the tag** — this is what triggers the publish:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
5. Watch **Actions → Release**. On success, verify at <https://pypi.org/project/whereq.cloud/>:
   ```bash
   gh run watch --exit-status   # optional
   curl -s https://pypi.org/pypi/whereq.cloud/json | python -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"
   ```

That's it. `pip install -U whereq.cloud` picks up the new version within a minute or two.

> **The step people forget.** Pushing to `main` does not publish — only the **tag** does.
> A feature merged without a version bump and a tag sits on PyPI forever without anyone
> noticing, because CI stays green. That is why `release.sh` checks for an existing tag
> and an existing PyPI version *before* it touches anything.

## Rules / gotchas

- **Tag must match the version** in `pyproject.toml` (tag `v0.2.0` ⇒ version `0.2.0`). A mismatch
  publishes the version in `pyproject.toml`, not the tag string. The `Release` workflow now
  **fails fast** on a mismatch (`verify the tag matches the package version`) instead of
  uploading a stale version and having PyPI reject it as a duplicate.
- **Never re-use a version** — PyPI refuses to overwrite an existing version. Bump and re-tag.
- `__version__` in `src/whereq_cloud/client.py` must equal the `pyproject.toml` version —
  `test_version_matches_pyproject` enforces it, and the version also rides along in the
  `User-Agent` header.
- The release job runs the tests first (green bar) before building/publishing.
- Import name stays `whereq_cloud` regardless of the PyPI project name `whereq.cloud`.

## One-time setup (already done — for reference / disaster recovery)

- **PyPI Trusted Publisher** — pypi.org → Account → Publishing → *Add a pending publisher* (GitHub):
  - PyPI Project Name: `whereq.cloud`
  - Owner: `whereq` · Repository: `whereq-cloud-python`
  - Workflow name: `release.yml` · Environment name: `pypi`
- **GitHub Environment** named `pypi` on this repo (Settings → Environments). **No secrets needed**
  (OIDC). Optionally restrict its deployment to tags matching `v*`.
- Workflow: `.github/workflows/release.yml` (trigger `push: tags: ["v*"]`, `permissions: id-token: write`).
