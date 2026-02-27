# eks-addons

List default AWS EKS add-on versions compatible with a given Kubernetes version.

## Install (editable/dev)
pip install -e .

## Usage
eks-addons --help

# Table output (default)
eks-addons -k 1.29
eks-addons -k 1.29 -r us-west-2

# Only a specific add-on
eks-addons -k 1.29 -a vpc-cni

# Output formats
eks-addons -k 1.29 -o json
eks-addons -k 1.29 -o yaml
eks-addons -k 1.29 -o hcl --hcl-var addon_defaults

# Disable colors
eks-addons -k 1.29 --no-color

## Notes
- Requires AWS CLI configured and credentials allowing `eks:DescribeAddonVersions`.
- Colors only apply to `-o table` and only when output is a TTY (not piped).

## License

MIT. See [LICENSE](LICENSE).
