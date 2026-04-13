"""
Changelog AI MCP Server
Changelog and version management tools powered by MEOK AI Labs.
"""

import re
import time
from collections import defaultdict
from datetime import date
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("changelog-ai-mcp")

_call_counts: dict[str, list[float]] = defaultdict(list)
FREE_TIER_LIMIT = 50
WINDOW = 86400

def _check_rate_limit(tool_name: str) -> None:
    now = time.time()
    _call_counts[tool_name] = [t for t in _call_counts[tool_name] if now - t < WINDOW]
    if len(_call_counts[tool_name]) >= FREE_TIER_LIMIT:
        raise ValueError(f"Rate limit exceeded for {tool_name}. Free tier: {FREE_TIER_LIMIT}/day. Upgrade at https://meok.ai/pricing")
    _call_counts[tool_name].append(now)


@mcp.tool()
def parse_changelog(content: str) -> dict:
    """Parse a Keep a Changelog format file into structured data.

    Args:
        content: Changelog content in markdown format
    """
    _check_rate_limit("parse_changelog")
    versions = []
    current = None
    current_section = None
    for line in content.split('\n'):
        # Match version headers like ## [1.0.0] - 2024-01-01 or ## 1.0.0
        ver_match = re.match(r'^##\s+\[?(\d+\.\d+\.\d+(?:-[\w.]+)?)\]?\s*(?:-\s*(.+))?', line)
        if ver_match:
            if current:
                versions.append(current)
            current = {"version": ver_match.group(1), "date": (ver_match.group(2) or "").strip(),
                       "sections": {}, "entry_count": 0}
            current_section = None
            continue
        # Match section headers like ### Added
        sec_match = re.match(r'^###\s+(.+)', line)
        if sec_match and current:
            current_section = sec_match.group(1).strip()
            current["sections"][current_section] = []
            continue
        # Match list items
        item_match = re.match(r'^[-*]\s+(.+)', line)
        if item_match and current and current_section:
            current["sections"][current_section].append(item_match.group(1).strip())
            current["entry_count"] += 1
    if current:
        versions.append(current)
    return {"versions": versions, "version_count": len(versions),
            "latest": versions[0]["version"] if versions else None,
            "total_entries": sum(v["entry_count"] for v in versions)}


@mcp.tool()
def generate_entry(
    version: str, changes: dict, release_date: str = ""
) -> dict:
    """Generate a changelog entry in Keep a Changelog format.

    Args:
        version: Version string (e.g., '1.2.0')
        changes: Dict with keys from: Added, Changed, Deprecated, Removed, Fixed, Security
        release_date: Release date (default: today)
    """
    _check_rate_limit("generate_entry")
    valid_sections = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}
    if not release_date:
        release_date = date.today().isoformat()
    lines = [f"## [{version}] - {release_date}", ""]
    entry_count = 0
    for section in ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]:
        items = changes.get(section, [])
        if items:
            lines.append(f"### {section}")
            for item in items:
                lines.append(f"- {item}")
                entry_count += 1
            lines.append("")
    invalid = [k for k in changes if k not in valid_sections]
    result = {"entry": "\n".join(lines), "version": version, "date": release_date,
              "entry_count": entry_count, "sections_used": [s for s in valid_sections if changes.get(s)]}
    if invalid:
        result["warnings"] = [f"Non-standard section: {k}" for k in invalid]
    return result


@mcp.tool()
def bump_version(
    current: str, bump_type: str = "patch", pre_release: str = ""
) -> dict:
    """Bump a semantic version number.

    Args:
        current: Current version (e.g., '1.2.3')
        bump_type: 'major', 'minor', or 'patch'
        pre_release: Pre-release label (e.g., 'alpha', 'beta.1', 'rc.1')
    """
    _check_rate_limit("bump_version")
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', current.strip())
    if not match:
        return {"error": f"Invalid semver: {current}"}
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    old_pre = match.group(4) or ""
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        return {"error": f"Invalid bump_type: {bump_type}. Use major, minor, or patch."}
    new_version = f"{major}.{minor}.{patch}"
    if pre_release:
        new_version += f"-{pre_release}"
    return {"previous": current, "new": new_version, "bump_type": bump_type,
            "major": major, "minor": minor, "patch": patch,
            "pre_release": pre_release or None, "is_breaking": bump_type == "major"}


@mcp.tool()
def compare_versions(version_a: str, version_b: str) -> dict:
    """Compare two semantic versions and determine ordering.

    Args:
        version_a: First version string
        version_b: Second version string
    """
    _check_rate_limit("compare_versions")
    def parse(v):
        m = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', v.strip())
        if not m:
            return None
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "")
    a = parse(version_a)
    b = parse(version_b)
    if not a:
        return {"error": f"Invalid version: {version_a}"}
    if not b:
        return {"error": f"Invalid version: {version_b}"}
    core_a, core_b = a[:3], b[:3]
    if core_a > core_b:
        comparison = "greater"
        result = 1
    elif core_a < core_b:
        comparison = "lesser"
        result = -1
    else:
        if a[3] == b[3]:
            comparison = "equal"
            result = 0
        elif a[3] and not b[3]:
            comparison = "lesser"  # pre-release < release
            result = -1
        elif not a[3] and b[3]:
            comparison = "greater"
            result = 1
        else:
            comparison = "greater" if a[3] > b[3] else "lesser"
            result = 1 if a[3] > b[3] else -1
    diff_type = "none"
    if core_a[0] != core_b[0]:
        diff_type = "major"
    elif core_a[1] != core_b[1]:
        diff_type = "minor"
    elif core_a[2] != core_b[2]:
        diff_type = "patch"
    elif a[3] != b[3]:
        diff_type = "pre-release"
    return {"version_a": version_a, "version_b": version_b,
            "comparison": comparison, "result": result,
            "difference_type": diff_type,
            "a_is_newer": result > 0, "b_is_newer": result < 0, "are_equal": result == 0}


if __name__ == "__main__":
    mcp.run()
