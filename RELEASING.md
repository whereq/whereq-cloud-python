# Releasing `whereq.cloud` (Python → PyPI)

Publishing is automated: **push a version tag `vX.Y.Z` and GitHub Actions publishes to PyPI
via Trusted Publishing (OIDC).** No tokens are stored anywhere.

## Release a new version (the recurring steps)

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

## Rules / gotchas

- **Tag must match the version** in `pyproject.toml` (tag `v0.2.0` ⇒ version `0.2.0`). A mismatch
  publishes the version in `pyproject.toml`, not the tag string.
- **Never re-use a version** — PyPI refuses to overwrite an existing version. Bump and re-tag.
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
