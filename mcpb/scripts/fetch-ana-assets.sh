#!/usr/bin/env bash
# Copyright (c) Anaconda, Inc.
#
# Apache-2.0 License

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCPB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHECKSUMS="${MCPB_DIR}/ana-assets.sha256"
BIN_DIR="${MCPB_DIR}/bin"

VERSION="${ANA_CLI_VERSION:-}"
if [[ -z "${VERSION}" ]]; then
  VERSION="$(sed -n 's/^# ana-cli release: //p' "${CHECKSUMS}" | head -n 1)"
fi

if [[ -z "${VERSION}" ]]; then
  echo "Could not determine ana CLI release version" >&2
  exit 1
fi

BASE_URL="https://github.com/anaconda/anaconda-cli/releases/download/${VERSION}"
mkdir -p "${BIN_DIR}"

while read -r expected_sha asset_name; do
  [[ -z "${expected_sha:-}" ]] && continue
  [[ "${expected_sha}" == \#* ]] && continue

  output_path="${BIN_DIR}/${asset_name}"
  url="${BASE_URL}/${asset_name}"

  echo "Fetching ${url}"
  curl -LfsS "${url}" -o "${output_path}"
  printf '%s  %s\n' "${expected_sha}" "${output_path}" | shasum -a 256 -c -

  if [[ "${asset_name}" != *.exe ]]; then
    chmod 755 "${output_path}"
  fi
done < "${CHECKSUMS}"
