import re
import click

_K8S_RE = re.compile(r"^(1)\.(\d{1,2})$")
_REGION_RE = re.compile(r"^[a-z]{2}(-gov)?-[a-z]+-\d+$")
_ADDON_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_k8s_version(_: click.Context, __: click.Parameter, value: str) -> str:
    if value is None:
        return value
    v = value.strip()
    m = _K8S_RE.match(v)
    if not m:
        raise click.BadParameter("must look like '1.29' (major.minor).")
    minor = int(m.group(2))
    if minor < 10 or minor > 35:
        raise click.BadParameter("minor version looks invalid (expected something like 1.2x).")
    return v


def validate_region(_: click.Context, __: click.Parameter, value: str) -> str:
    if value is None:
        return value
    r = value.strip()
    if not _REGION_RE.match(r):
        raise click.BadParameter("must look like 'us-east-1', 'us-west-2', 'eu-west-1', etc.")
    return r


def validate_addon(_: click.Context, __: click.Parameter, value: str) -> str:
    if value is None:
        return value
    a = value.strip()
    if not _ADDON_RE.match(a):
        raise click.BadParameter("must be lowercase letters/digits/hyphens (e.g., 'vpc-cni').")
    return a
