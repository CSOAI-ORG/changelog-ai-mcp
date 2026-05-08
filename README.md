<div align="center">

# Changelog Ai MCP

**Changelog AI MCP Server**

[![PyPI](https://img.shields.io/pypi/v/meok-changelog-ai-mcp)](https://pypi.org/project/meok-changelog-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Changelog AI MCP Server
Changelog and versioning tools powered by MEOK AI Labs.

## Tools

| Tool | Description |
|------|-------------|
| `parse_changelog` | Parse a Keep-a-Changelog format changelog into structured data. |
| `generate_entry` | Generate a changelog entry in Keep-a-Changelog format. |
| `bump_version` | Bump a semantic version number. |
| `compare_versions` | Compare two semantic versions and determine their relationship. |

## Installation

```bash
pip install meok-changelog-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "changelog-ai": {
      "command": "python",
      "args": ["-m", "meok_changelog_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 4 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
