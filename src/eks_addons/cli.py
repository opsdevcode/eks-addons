#!/usr/bin/env python3
import os
import sys
import re
from typing import Optional, List, Dict, Any

import click
from colorama import init as color_init

from eks_addons.aws_cli import run_aws_json
from eks_addons.output import (
    normalize_results,
    render_table,
    render_json,
    render_yaml,
    to_hcl_map,
)

# ----------------------------
# Click ParamTypes (kept here to avoid import drift)
# ----------------------------

_K8S_RE = re.compile(r"^(1)\.(\d{1,2})$")
_REGION_RE = re.compile(r"^[a-z]{2}(-gov)?-[a-z]+-\d+$")
_ADDON_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


class K8sVersionParam(click.ParamType):
    name = "k8s_version"

    def convert(self, value, param, ctx):
        v = (value or "").strip()
        m = _K8S_RE.match(v)
        if not m:
            self.fail("must look like '1.29' (major.minor).", param, ctx)
        minor = int(m.group(2))
        if minor < 10 or minor > 35:
            self.fail("minor version looks invalid (expected something like 1.2x).", param, ctx)
        return v


class RegionParam(click.ParamType):
    name = "aws_region"

    def convert(self, value, param, ctx):
        r = (value or "").strip()
        if not _REGION_RE.match(r):
            self.fail("must look like 'us-east-1', 'us-west-2', 'eu-west-1', etc.", param, ctx)
        return r


class AddonListParam(click.ParamType):
    """
    Accepts a single add-on (vpc-cni) or a CSV list (vpc-cni,coredns,kube-proxy).
    Returns: List[str] or None
    """

    name = "addon_list"

    def convert(self, value, param, ctx):
        if value is None:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        addons = [a.strip() for a in raw.split(",") if a.strip()]
        if not addons:
            return None

        invalid = [a for a in addons if not _ADDON_RE.match(a)]
        if invalid:
            self.fail(
                f"invalid add-on name(s): {', '.join(invalid)} "
                "(must be lowercase letters/digits/hyphens)",
                param,
                ctx,
            )
        return addons


K8S_VERSION = K8sVersionParam()
AWS_REGION = RegionParam()
ADDON_LIST = AddonListParam()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-k",
    "--k8s-version",
    type=K8S_VERSION,
    default="1.29",
    show_default=True,
    help="Kubernetes version (major.minor).",
)
@click.option(
    "-r",
    "--region",
    type=AWS_REGION,
    default=lambda: os.getenv("AWS_REGION", "us-east-1"),
    show_default="AWS_REGION or us-east-1",
    help="AWS region.",
)
@click.option(
    "-a",
    "--addon",
    "addons",
    type=ADDON_LIST,
    default=None,
    help="Comma-separated list of add-ons (e.g., vpc-cni,coredns,kube-proxy).",
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["table", "json", "yaml", "hcl"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--hcl-var",
    default="eks_addon_versions",
    show_default=True,
    help="HCL variable name (only used when --output hcl).",
)
@click.option("--no-color", is_flag=True, help="Disable colorized output (table only).")
@click.option(
    "-l",
    "--latest-only",
    is_flag=True,
    help="Only show latest compatible version (omit default).",
)
@click.option(
    "-u",
    "--upgradable",
    is_flag=True,
    help="Only show add-ons where latest != default.",
)
@click.option(
    "--timeout",
    type=int,
    default=lambda: int(os.getenv("EKS_ADDONS_TIMEOUT", "30")),
    show_default="30 (or env EKS_ADDONS_TIMEOUT)",
    help="AWS CLI timeout seconds.",
)
@click.option(
    "--retries",
    type=int,
    default=lambda: int(os.getenv("EKS_ADDONS_RETRIES", "2")),
    show_default="2 (or env EKS_ADDONS_RETRIES)",
    help="Retries for transient/network errors.",
)
@click.option(
    "--retry-delay",
    type=float,
    default=lambda: float(os.getenv("EKS_ADDONS_RETRY_DELAY", "0.75")),
    show_default="0.75 (or env EKS_ADDONS_RETRY_DELAY)",
    help="Base retry delay seconds (exponential backoff).",
)
def main(
    k8s_version: str,
    region: str,
    addons: Optional[List[str]],
    output: str,
    hcl_var: str,
    no_color: bool,
    latest_only: bool,
    upgradable: bool,
    timeout: int,
    retries: int,
    retry_delay: float,
) -> None:
    """List default and latest AWS EKS add-on versions for a given Kubernetes version."""
    color_init()

    if timeout <= 0:
        raise click.BadParameter("--timeout must be a positive integer.")
    if retries < 0:
        raise click.BadParameter("--retries must be >= 0.")
    if retry_delay <= 0:
        raise click.BadParameter("--retry-delay must be > 0.")

    # AWS CLI supports only a single --addon-name; optimize for that case.
    cmd = [
        "aws",
        "eks",
        "describe-addon-versions",
        "--region",
        region,
        "--kubernetes-version",
        k8s_version,
        "--output",
        "json",
    ]
    if addons and len(addons) == 1:
        cmd.extend(["--addon-name", addons[0]])

    try:
        data: Dict[str, Any] = run_aws_json(cmd=cmd, timeout=timeout, retries=retries, retry_delay=retry_delay)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from None

    results = normalize_results(data)

    # Client-side filtering for multiple addons (or if AWS returned more than requested).
    if addons:
        wanted = set(addons)
        results = [r for r in results if r.get("addon") in wanted]

        found = {r.get("addon") for r in results}
        missing = wanted - found
        if missing:
            raise click.ClickException(
                f"Add-on(s) not found for Kubernetes {k8s_version} in {region}: {', '.join(sorted(missing))}"
            )

    # Filter: only upgradable (latest != default)
    if upgradable:
        filtered = []
        for r in results:
            dv = (r.get("defaultVersion") or "")
            lv = (r.get("latestVersion") or "")
            if dv and lv and lv != dv:
                filtered.append(r)
        results = filtered

    # Shape: latest-only output
    if latest_only:
        results = [
            {"addon": r["addon"], "latestVersion": r.get("latestVersion")}
            for r in results
        ]

    use_color = sys.stdout.isatty() and (not no_color) and (output.lower() == "table")

    out = output.lower()
    if out == "json":
        click.echo(render_json(results))
    elif out == "yaml":
        click.echo(render_yaml(results))
    elif out == "hcl":
        click.echo(to_hcl_map(results, var_name=hcl_var))
    else:
        click.echo(render_table(results, use_color=use_color))
