"""Tests for eks-addons CLI."""

import pytest
from click.testing import CliRunner

from eks_addons.cli import main


def test_cli_help():
    """CLI --help exits 0 and shows usage."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "EKS" in result.output or "add-on" in result.output
    assert "k8s" in result.output or "Kubernetes" in result.output
