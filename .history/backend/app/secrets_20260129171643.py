import os
from typing import List, Optional


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def load_docker_secrets(names: List[str]) -> None:
    """Load Docker secrets (mounted at /run/secrets/<name>) into environment.

    For each name in `names`, this will check `/run/secrets/{name}` and
    `/run/secrets/{name.lower()}` and, if found, set the corresponding
    environment variable to the file contents.
    """
    base = "/run/secrets"
    for name in names:
        candidates = [name, name.lower()]
        for cand in candidates:
            path = os.path.join(base, cand)
            val = _read_file(path)
            if val:
                os.environ[name] = val
                break


def load_local_secret_file(path: str, env_name: str) -> None:
    """Load a single secret file into an env var if it exists."""
    val = _read_file(path)
    if val:
        os.environ[env_name] = val


def try_load_aws_secret(secret_name: str, env_name: str) -> None:
    """Attempt to load a secret from AWS Secrets Manager into an env var.

    This is optional — if `boto3` is not installed or AWS creds are not
    configured, this does nothing.
    """
    try:
        import boto3
        import base64
        from botocore.exceptions import BotoCoreError, ClientError

        client = boto3.client("secretsmanager")
        resp = client.get_secret_value(SecretId=secret_name)
        secret = resp.get("SecretString")
        if not secret and resp.get("SecretBinary"):
            secret = base64.b64decode(resp["SecretBinary"]).decode("utf-8")
        if secret:
            os.environ[env_name] = secret.strip()
    except Exception:
        # Don't fail if aws retrieval isn't available or fails.
        return
