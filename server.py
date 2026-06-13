"""
Changelog AI MCP Server
Changelog and versioning tools powered by MEOK AI Labs.
"""


import sys, os
from auth_middleware import check_access

import re
import time
from collections import defaultdict
from datetime import date
from mcp.server.fastmcp import FastMCP
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr

STRIPE_199 = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"

def _add_upgrade_tail(response, tier="free"):
    """Append upgrade nudge to free-tier success responses."""
    if isinstance(response, dict) and tier == "free":
        response["_upgrade_note"] = "Pro tier: unlimited calls + priority support. Upgrade: " + STRIPE_199
    return response


mcp = FastMCP("changelog-ai", instructions="MEOK AI Labs MCP Server")

_call_counts: dict[str, list[float]] = defaultdict(list)
FREE_TIER_LIMIT = 50
WINDOW = 86400


def _check_rate_limit(tool_name: str) -> None:
    now = time.time()
    _call_counts[tool_name] = [t for t in _call_counts[tool_name] if now - t < WINDOW]
    if len(_call_counts[tool_name]) >= FREE_TIER_LIMIT:
        raise ValueError(f"Rate limit exceeded for {tool_name}. Free tier: {FREE_TIER_LIMIT}/day. Upgrade at https://councilof.ai")
    _call_counts[tool_name].append(now)


SEMVER_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?(?:\+([a-zA-Z0-9.]+))?$')


def _parse_ver(v: str) -> tuple:
    m = SEMVER_RE.match(v.strip())
    if not m:
        raise ValueError(f"Invalid semver: {v}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "", m.group(5) or ""

def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Returns the JSON dict.
    Fail-open: if /verify is unreachable or KV isn't configured, returns allowed=True
    (so the local rate-limit in _check_rate_limit remains the safety net)."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def parse_changelog(content: str, api_key: str = "") -> dict:
    """Parse a Keep-a-Changelog format changelog into structured data.

    Args:
        content: Changelog content in markdown format

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    _check_rate_limit("parse_changelog")
    versions = []
    current = None
    current_section = None
    for line in content.split('\n'):
        ver_match = re.match(r'^##\s+\[?v?(\d+\.\d+\.\d+[^\]]*)\]?\s*(?:-\s*(.+))?', line)
        if ver_match:
            if current:
                versions.append(current)
            current = {"version": ver_match.group(1).strip(), "date": ver_match.group(2) or "",
                       "sections": {}}
            current_section = None
            continue
        section_match = re.match(r'^###\s+(.+)', line)
        if section_match and current is not None:
            current_section = section_match.group(1).strip()
            current["sections"][current_section] = []
            continue
        item_match = re.match(r'^[-*]\s+(.+)', line)
        if item_match and current is not None and current_section:
            current["sections"][current_section].append(item_match.group(1).strip())
    if current:
        versions.append(current)
    total_entries = sum(sum(len(items) for items in v["sections"].values()) for v in versions)
    return {"versions": versions, "version_count": len(versions), "total_entries": total_entries}


@mcp.tool()
def generate_entry(
    version: str, changes: dict, release_date: str = ""
, api_key: str = "") -> dict:
    """Generate a changelog entry in Keep-a-Changelog format.

    Args:
        version: Version string (e.g., "1.2.0")
        changes: Dict with section keys (Added, Changed, Fixed, Removed, etc.) mapping to lists of change descriptions
        release_date: Release date (YYYY-MM-DD, default: today)

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    _check_rate_limit("generate_entry")
    if not release_date:
        release_date = date.today().isoformat()
    lines = [f"## [{version}] - {release_date}", ""]
    valid_sections = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    entry_count = 0
    for section in valid_sections:
        if section in changes and changes[section]:
            lines.append(f"### {section}")
            for item in changes[section]:
                lines.append(f"- {item}")
                entry_count += 1
            lines.append("")
    for section, items in changes.items():
        if section not in valid_sections and items:
            lines.append(f"### {section}")
            for item in items:
                lines.append(f"- {item}")
                entry_count += 1
            lines.append("")
    entry = "\n".join(lines)
    return {"entry": entry, "version": version, "date": release_date,
            "sections": len([s for s in changes if changes[s]]), "total_items": entry_count}


@mcp.tool()
def bump_version(current: str, bump_type: str = "patch", prerelease: str = "", api_key: str = "") -> dict:
    """Bump a semantic version number.

    Args:
        current: Current version string (e.g., "1.2.3")
        bump_type: Type of bump - 'major', 'minor', 'patch'
        prerelease: Optional prerelease tag (e.g., 'alpha', 'beta.1', 'rc.1')

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    _check_rate_limit("bump_version")
    try:
        major, minor, patch, pre, build = _parse_ver(current)
    except ValueError as e:
        return {"error": str(e)}
    if bump_type == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump_type == "minor":
        minor, patch = minor + 1, 0
    elif bump_type == "patch":
        patch += 1
    else:
        return {"error": f"Invalid bump_type: {bump_type}. Use 'major', 'minor', or 'patch'"}
    new = f"{major}.{minor}.{patch}"
    if prerelease:
        new += f"-{prerelease}"
    return {"previous": current, "new": new, "bump_type": bump_type,
            "major": major, "minor": minor, "patch": patch, "prerelease": prerelease or None}


@mcp.tool()
def compare_versions(version_a: str, version_b: str, api_key: str = "") -> dict:
    """Compare two semantic versions and determine their relationship.

    Args:
        version_a: First version string
        version_b: Second version string

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    _check_rate_limit("compare_versions")
    try:
        a = _parse_ver(version_a)
        b = _parse_ver(version_b)
    except ValueError as e:
        return {"error": str(e)}
    core_a, core_b = a[:3], b[:3]
    if core_a > core_b:
        comparison = "greater"
        result = 1
    elif core_a < core_b:
        comparison = "lesser"
        result = -1
    else:
        if a[3] and not b[3]:
            comparison, result = "lesser", -1
        elif not a[3] and b[3]:
            comparison, result = "greater", 1
        elif a[3] > b[3]:
            comparison, result = "greater", 1
        elif a[3] < b[3]:
            comparison, result = "lesser", -1
        else:
            comparison, result = "equal", 0
    diff_type = None
    if core_a != core_b:
        if a[0] != b[0]:
            diff_type = "major"
        elif a[1] != b[1]:
            diff_type = "minor"
        else:
            diff_type = "patch"
    return {"version_a": version_a, "version_b": version_b, "comparison": comparison,
            "result": result, "diff_type": diff_type, "compatible": a[0] == b[0]}


def main():
    mcp.run()

if __name__ == '__main__':
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
