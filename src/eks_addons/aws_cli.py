import json
import time
import subprocess
from typing import Any, Dict, List, Optional

RETRYABLE_SUBSTRINGS = (
    "RequestError",
    "Connection timed out",
    "Connection reset by peer",
    "Could not connect to the endpoint URL",
    "Temporary failure in name resolution",
    "Name or service not known",
    "EOF occurred in violation of protocol",
    "TLSV1_ALERT",
    "ServiceUnavailable",
    "Throttling",
    "TooManyRequestsException",
    "InternalFailure",
    "InternalServerError",
    "503",
)


def is_retryable_error(stderr: str) -> bool:
    s = (stderr or "").strip()
    return any(sub in s for sub in RETRYABLE_SUBSTRINGS)


def run_aws_json(cmd: List[str], timeout: int, retries: int, retry_delay: float) -> Dict[str, Any]:
    last_err: Optional[str] = None

    for attempt in range(retries + 1):
        try:
            p = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            raise RuntimeError("aws CLI not found. Install AWS CLI v2 and ensure 'aws' is on PATH.") from None
        except subprocess.TimeoutExpired:
            last_err = f"Timed out after {timeout}s running AWS CLI."
        else:
            if p.returncode == 0:
                try:
                    return json.loads(p.stdout)
                except json.JSONDecodeError:
                    raise RuntimeError(
                        "AWS CLI returned non-JSON output. Check proxies/network and try again."
                    ) from None

            last_err = (p.stderr or "").strip() or "AWS CLI command failed."

            # clearer messages for common issues
            if "UnrecognizedClientException" in last_err or "InvalidClientTokenId" in last_err:
                raise RuntimeError("AWS credentials are invalid/expired. Re-authenticate and try again.") from None
            if "AccessDenied" in last_err or "AccessDeniedException" in last_err:
                raise RuntimeError("Access denied. Need permission: eks:DescribeAddonVersions.") from None
            if "NoCredentialProviders" in last_err or "Unable to locate credentials" in last_err:
                raise RuntimeError("No AWS credentials found. Configure credentials and try again.") from None
            if "InvalidParameterException" in last_err and "--addon-name" in " ".join(cmd):
                raise RuntimeError(
                    "Invalid add-on name for this region/Kubernetes version. "
                    "Double-check the add-on name (e.g., vpc-cni, coredns, kube-proxy)."
                ) from None

            if not is_retryable_error(last_err):
                raise RuntimeError(last_err) from None

        if attempt < retries:
            time.sleep(retry_delay * (2 ** attempt))

    raise RuntimeError(last_err or "AWS CLI failed after retries.")
