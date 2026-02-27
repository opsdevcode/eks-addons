"""Tests for eks-addons validation."""

import pytest
import click

from eks_addons.validate import validate_k8s_version, validate_region, validate_addon


def test_validate_k8s_version_valid():
    """Valid k8s versions pass."""
    assert validate_k8s_version(None, None, "1.29") == "1.29"
    assert validate_k8s_version(None, None, "1.10") == "1.10"
    assert validate_k8s_version(None, None, "1.35") == "1.35"


def test_validate_k8s_version_invalid_format():
    """Invalid format raises BadParameter."""
    with pytest.raises(click.BadParameter, match="must look like"):
        validate_k8s_version(None, None, "2.0")
    with pytest.raises(click.BadParameter, match="must look like"):
        validate_k8s_version(None, None, "abc")


def test_validate_k8s_version_invalid_minor_range():
    """Minor version outside 10-35 raises BadParameter."""
    with pytest.raises(click.BadParameter, match="minor version"):
        validate_k8s_version(None, None, "1.9")


def test_validate_region_valid():
    """Valid regions pass."""
    assert validate_region(None, None, "us-east-1") == "us-east-1"
    assert validate_region(None, None, "us-west-2") == "us-west-2"
    assert validate_region(None, None, "eu-west-1") == "eu-west-1"


def test_validate_region_invalid():
    """Invalid region raises BadParameter."""
    with pytest.raises(click.BadParameter, match="must look like"):
        validate_region(None, None, "invalid")
    with pytest.raises(click.BadParameter, match="must look like"):
        validate_region(None, None, "use1")


def test_validate_addon_valid():
    """Valid addon names pass."""
    assert validate_addon(None, None, "vpc-cni") == "vpc-cni"
    assert validate_addon(None, None, "coredns") == "coredns"
    assert validate_addon(None, None, "kube-proxy") == "kube-proxy"


def test_validate_addon_invalid():
    """Invalid addon raises BadParameter."""
    with pytest.raises(click.BadParameter, match="lowercase"):
        validate_addon(None, None, "VPC-CNI")
    with pytest.raises(click.BadParameter, match="lowercase"):
        validate_addon(None, None, "vpc_cni")
