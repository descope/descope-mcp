# Release Process

Releases of the `descope-mcp` Python package are fully automated with
[Release Please](https://github.com/googleapis/release-please) and published to
PyPI with [trusted publishing](https://docs.pypi.org/trusted-publishers/). Nobody
bumps versions, edits `CHANGELOG.md`, creates tags, or uploads to PyPI by hand.

## How a release happens

1. Merge pull requests into `main`. PRs are squash-merged and the **PR title**
   becomes the commit message, so it must follow
   [Conventional Commits](https://www.conventionalcommits.org/) (CI enforces this):

   | PR title                                         | Release effect |
   | ------------------------------------------------ | -------------- |
   | `fix: ...` / `deps: ...`                          | patch          |
   | `feat: ...`                                       | minor          |
   | `feat!: ...` or a `BREAKING CHANGE:` footer       | major          |
   | `docs:`, `chore:`, `ci:`, `build:`, `test:`, ... | no release     |

2. The [Release Please workflow](.github/workflows/release-please.yml) opens or
   updates a release PR titled `chore(main): release descope-mcp X.Y.Z`. It owns
   every version-bearing file:
   - `.release-please-manifest.json`
   - `CHANGELOG.md`
   - `python/pyproject.toml` (`project.version`)
   - `python/uv.lock` (the `descope-mcp` package entry)
   - `python/src/descope_mcp/__init__.py` (`__version__`, marked `x-release-please-version`)

   See [`release-please-config.json`](release-please-config.json).

3. Review and merge the release PR. The workflow then:
   1. creates the `descope-mcp-vX.Y.Z` tag and GitHub Release (via the Descope Release Bot app),
   2. builds the sdist and wheel from the tag and checks their version matches the release,
   3. records [build provenance attestations](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations),
   4. publishes to PyPI from the `pypi` environment using OIDC. PyPI also gets
      [PEP 740](https://peps.python.org/pep-0740/) attestations.

### Choosing an exact version

Only when a specific version is required, put a `Release-As` footer in the merged
commit body:

```text
chore: release 1.0.0

Release-As: 1.0.0
```

### Fixing release notes after merge

Edit the body of the merged PR and add:

```text
BEGIN_COMMIT_OVERRIDE
fix(python): corrected release-note entry
END_COMMIT_OVERRIDE
```

The next Release Please run regenerates the release PR.

## Supply-chain controls

- **No long-lived PyPI credentials.** The publish job exchanges a short-lived
  GitHub OIDC token with PyPI. Build and publish run as separate jobs, and only
  the publish job can mint the token.
- **Pinned actions.** Every action is pinned to a full commit SHA. Renovate keeps the pins current.
- **Least privilege.** Workflows default to `permissions: {}` and each job asks
  only for what it uses. The release app token is limited to contents, issues
  and pull requests.
- **Workflow auditing.** [zizmor](https://docs.zizmor.sh/) and gitleaks run on every PR.
- **Rulesets.** `main` requires PR review and the `CI OK` check. Release tags
  (`descope-mcp-v*`) can only be created by the release app, and cannot be moved
  or deleted. The definitions are in [`.github/rulesets`](.github/rulesets).

## One-time PyPI setup

The trusted publisher on <https://pypi.org/manage/project/descope-mcp/settings/publishing/>
must match:

| Field       | Value                |
| ----------- | -------------------- |
| Owner       | `descope`            |
| Repository  | `descope-mcp`        |
| Workflow    | `release-please.yml` |
| Environment | `pypi`               |

Once trusted publishing works, delete any PyPI API tokens for the project.

## Troubleshooting

- **No release PR appeared:** check that a releasable commit (`feat`, `fix`, `deps`,
  or breaking) landed on `main`, and that the Release Please workflow succeeded.
  Also look for an old PR still labelled `autorelease: pending`.
- **Publish failed with "file already exists":** the built version did not match
  the release. The *Verify distributions* step is meant to catch this before upload.
  Check the extra-files in `release-please-config.json`.
- **`invalid-publisher` from PyPI:** the trusted publisher settings above do not
  match the workflow file name or environment name.
