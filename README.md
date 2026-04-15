# Changelog AI MCP Server

> By [MEOK AI Labs](https://meok.ai) — Changelog parsing, generation, and semantic version management

## Installation

```bash
pip install changelog-ai-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install changelog-ai-mcp
```

## Tools

### `parse_changelog`
Parse a Keep-a-Changelog format changelog into structured data with version history.

**Parameters:**
- `content` (str): Changelog content in markdown format

### `generate_entry`
Generate a changelog entry in Keep-a-Changelog format with sections (Added, Changed, Fixed, Removed, etc.).

**Parameters:**
- `version` (str): Version string (e.g., '1.2.0')
- `changes` (dict): Dict mapping section names to lists of change descriptions
- `release_date` (str): Release date YYYY-MM-DD (default: today)

### `bump_version`
Bump a semantic version number (major, minor, or patch) with optional prerelease tag.

**Parameters:**
- `current` (str): Current version string (e.g., '1.2.3')
- `bump_type` (str): Type of bump — 'major', 'minor', 'patch'
- `prerelease` (str): Optional prerelease tag (e.g., 'alpha', 'beta.1')

### `compare_versions`
Compare two semantic versions and determine their relationship (greater, lesser, equal).

**Parameters:**
- `version_a` (str): First version string
- `version_b` (str): Second version string

## Authentication

Free tier: 50 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## License

MIT — MEOK AI Labs
