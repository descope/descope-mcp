# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report it privately through
[GitHub private vulnerability reporting](https://github.com/descope/descope-mcp/security/advisories/new).
We will acknowledge your report, investigate, and keep you updated until it is resolved.

## Supported versions

Security fixes are released for the latest published version of
[`descope-mcp`](https://pypi.org/project/descope-mcp/).

## Verifying releases

Releases are published to PyPI with trusted publishing. Each distribution has
build provenance you can verify with the GitHub CLI:

```bash
pip download descope-mcp --no-deps -d dist
gh attestation verify dist/descope_mcp-*.whl --repo descope/descope-mcp
```
