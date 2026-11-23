#!/usr/bin/env bash
# Verify that a dist directory holds exactly the sdist and wheel for one version.
# Used by both CI (on every PR) and the release workflow, so a check that would
# fail at release time fails in PR CI first.
#
# Usage: verify-dist.sh <dist-dir> <version>
set -euo pipefail

dist_dir="${1:?usage: verify-dist.sh <dist-dir> <version>}"
version="${2:?usage: verify-dist.sh <dist-dir> <version>}"

wheel="${dist_dir}/descope_mcp-${version}-py3-none-any.whl"
sdist="${dist_dir}/descope_mcp-${version}.tar.gz"

test -f "${wheel}" || { echo "::error::missing ${wheel}"; exit 1; }
test -f "${sdist}" || { echo "::error::missing ${sdist}"; exit 1; }

# uv build also writes a .gitignore into the output directory; count only distributions.
count="$(find "${dist_dir}" -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' \) | wc -l | tr -d ' ')"
if [ "${count}" -ne 2 ]; then
  echo "::error::expected exactly 2 distributions in ${dist_dir}, found ${count}"
  find "${dist_dir}" -maxdepth 1 -type f
  exit 1
fi

uvx twine@7.0.0 check --strict "${wheel}" "${sdist}"
echo "dist OK: descope-mcp ${version}"
