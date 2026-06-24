# GitHub Release Download Snapshots

Anaconda MCP is listed in the MCP Registry as an MCPB package hosted on GitHub
Releases. The registry does not provide user-level install telemetry for that
package. The available top-of-funnel signal is GitHub's cumulative per-asset
`download_count` for the MCPB release asset.

The `GitHub Release Download Snapshot` workflow captures those counters four
times per day and stores each snapshot as a GitHub Actions artifact.

## Schedule

- `17 1,7,13,19 * * *` - scheduled snapshots in UTC.
- `workflow_dispatch` - manual snapshot.

## Artifact Contents

Each run uploads an artifact named
`github-release-download-snapshot-<run-id>` containing:

- `raw-release-pages.json` - raw paginated GitHub Releases API response.
- `release-asset-download-snapshot.json` - normalized release x asset rows.
- `release-asset-download-snapshot.csv` - CSV form of the normalized rows.
- `mcpb-release-download-snapshot.json` - filtered MCPB package rows.
- `mcpb-release-download-snapshot.csv` - CSV form of the filtered rows.

## Normalized Schema

The normalized files contain:

- `pulled_at`
- `repository`
- `release_id`
- `release_tag`
- `release_name`
- `release_created_at`
- `release_published_at`
- `release_prerelease`
- `release_draft`
- `release_html_url`
- `asset_id`
- `asset_name`
- `asset_content_type`
- `asset_size`
- `asset_created_at`
- `asset_updated_at`
- `browser_download_url`
- `digest`
- `download_count`

## Primary MCP Registry Metric

For MCP Registry package downloads, filter to:

- `release_tag` starts with `mcpb-`
- `asset_name = 'anaconda-mcp.mcpb'`

GitHub's `download_count` is cumulative. Daily, 7-day, and 30-day download
metrics should be derived by comparing snapshots, not by summing raw
`download_count` values.

This metric is not activated users, unique installs, or authenticated usage.
Activation and tool-use conversion still need to come from Anaconda MCP
telemetry.
