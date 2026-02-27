from typing import Any, Dict, List, Optional

import json
import yaml
from tabulate import tabulate
from colorama import Fore, Style


def _get_versions(addon_obj: Dict[str, Any]) -> List[str]:
    return [v["addonVersion"] for v in addon_obj.get("addonVersions", []) or []]


def get_default_version(addon_obj: Dict[str, Any]) -> Optional[str]:
    for ver in addon_obj.get("addonVersions", []) or []:
        comps = ver.get("compatibilities", []) or []
        if comps and comps[0].get("defaultVersion") is True:
            return ver.get("addonVersion")
    return None


def get_latest_version(addon_obj: Dict[str, Any]) -> Optional[str]:
    versions = _get_versions(addon_obj)
    return max(versions) if versions else None


def normalize_results(data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """
    Produces:
      [{
        addon,
        defaultVersion,
        latestVersion
      }]
    """
    results: List[Dict[str, Optional[str]]] = []

    for addon in data.get("addons", []) or []:
        results.append(
            {
                "addon": addon.get("addonName", ""),
                "defaultVersion": get_default_version(addon),
                "latestVersion": get_latest_version(addon),
            }
        )

    results.sort(key=lambda x: x["addon"])
    return results


def hcl_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_hcl_map(results: List[Dict[str, Optional[str]]], var_name: str) -> str:
    """
    Full shape -> addon => { default = "...", latest = "..." }
    Latest-only -> addon => { latest = "..." }
    """
    lines = [f"{var_name} = {{"]

    if not results:
        lines.append("}")
        return "\n".join(lines)

    latest_only = "defaultVersion" not in results[0]

    for r in results:
        lines.append(f"  {hcl_quote(r['addon'])} = {{")
        if not latest_only:
            lines.append(f"    default = {hcl_quote(r.get('defaultVersion') or '')}")
        lines.append(f"    latest  = {hcl_quote(r.get('latestVersion') or '')}")
        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)

def colorize(text: str, color: str, enable: bool) -> str:
    if not enable:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


def render_table(results: List[Dict[str, Optional[str]]], use_color: bool) -> str:
    if not results:
        return "(no results)"

    # latest-only shape
    if "defaultVersion" not in results[0]:
        rows = [
            [
                colorize(r["addon"], Fore.CYAN, use_color),
                colorize(r.get("latestVersion") or "", Fore.YELLOW, use_color),
            ]
            for r in results
        ]
        headers = [
            colorize("Add-on", Style.BRIGHT + Fore.WHITE, use_color),
            colorize("Latest", Style.BRIGHT + Fore.WHITE, use_color),
        ]
        return tabulate(rows, headers=headers, tablefmt="github")

    # full shape
    rows = [
        [
            colorize(r["addon"], Fore.CYAN, use_color),
            colorize(r.get("defaultVersion") or "", Fore.GREEN, use_color),
            colorize(r.get("latestVersion") or "", Fore.YELLOW, use_color),
        ]
        for r in results
    ]
    headers = [
        colorize("Add-on", Style.BRIGHT + Fore.WHITE, use_color),
        colorize("Default", Style.BRIGHT + Fore.WHITE, use_color),
        colorize("Latest", Style.BRIGHT + Fore.WHITE, use_color),
    ]
    return tabulate(rows, headers=headers, tablefmt="github")

def render_json(results: List[Dict[str, Optional[str]]]) -> str:
    return json.dumps(results, indent=2)


def render_yaml(results: List[Dict[str, Optional[str]]]) -> str:
    return yaml.safe_dump(results, sort_keys=False)
