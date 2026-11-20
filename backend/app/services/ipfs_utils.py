from __future__ import annotations

import base64
import hashlib
import re
from typing import Optional
from urllib.parse import urlparse

# CIDv0: Base58btc starting with Qm, typically 46 characters.
# CIDv1: Multibase prefix (e.g. 'b' for base32, 'z' for base58btc), starts with bafy, bafk, etc.
CID_REGEX = re.compile(r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{58,}|z[1-9A-HJ-NP-Za-km-z]{48,})(/.*)?$")


def normalize_cid(cid_or_uri: str) -> str:
    """Normalizes any CID, IPFS URI, gateway URL, or storage reference to a clean CID string.
    Safely removes all variations of redundant prefixes:
      - 'ipfs://'
      - 'ipfs:/'
      - 'ipfs:'
      - '/ipfs/'
      - 'local-sha256:'
      - Full gateway URLs like 'http://127.0.0.1:8080/ipfs/...'
    Preserves valid subpaths (e.g. 'bafy.../sample.cif').
    """
    if not isinstance(cid_or_uri, str):
        return ""

    clean = cid_or_uri.strip()
    if not clean:
        return ""

    # If a full HTTP/HTTPS gateway URL is provided, extract path after /ipfs/
    if clean.startswith("http://") or clean.startswith("https://"):
        try:
            parsed = urlparse(clean)
            path = parsed.path
            idx = path.find("/ipfs/")
            if idx != -1:
                clean = path[idx + 6 :]
            else:
                clean = path.lstrip("/")
        except Exception:
            pass

    # Iteratively strip redundant protocol and path prefixes
    changed = True
    while changed:
        before = clean
        clean = clean.strip()
        if clean.startswith("local-sha256:"):
            clean = clean[13:]
        elif clean.startswith("ipfs://"):
            clean = clean[7:]
        elif clean.startswith("ipfs:/"):
            clean = clean[6:]
        elif clean.startswith("ipfs:"):
            clean = clean[5:]
        elif clean.startswith("/ipfs/"):
            clean = clean[6:]
        elif clean.startswith("ipfs/"):
            clean = clean[5:]
        elif clean.startswith("/"):
            clean = clean.lstrip("/")

        changed = before != clean

    # Collapse any internal duplicate slashes
    while "//" in clean:
        clean = clean.replace("//", "/")

    return clean.strip("/")


def is_valid_cid(cid_or_uri: str) -> bool:
    """Validates whether the given string is or starts with a valid IPFS CID (CIDv0 or CIDv1)."""
    clean = normalize_cid(cid_or_uri)
    if not clean:
        return False
    # Check if the root component matches CID format
    root_cid = clean.split("/", 1)[0]
    return bool(CID_REGEX.match(root_cid))


def build_gateway_url(gateway_base: str, cid_or_uri: str) -> str:
    """Constructs a canonical IPFS gateway URL: http://{host}:{port}/ipfs/{CID}[/subpath].
    Never generates malformed paths such as /ipfs/ipfs:/... or duplicate /ipfs/ segments.
    """
    clean_cid = normalize_cid(cid_or_uri)
    if not clean_cid:
        return ""

    gw = (gateway_base or "http://127.0.0.1:8080").strip().rstrip("/")
    if gw.endswith("/ipfs"):
        gw = gw[:-5].rstrip("/")

    return f"{gw}/ipfs/{clean_cid}"


def build_ipfs_uri(cid_or_uri: str) -> str:
    """Constructs a canonical native IPFS URI: ipfs://{CID}[/subpath]."""
    clean_cid = normalize_cid(cid_or_uri)
    if not clean_cid:
        return ""
    return f"ipfs://{clean_cid}"


def compute_cidv1_raw_sha256(data: bytes) -> str:
    """Computes a standard IPFS CIDv1 multihash for raw binary or JSON data.
    Prefix:
      0x01: CIDv1
      0x55: raw multicodec
      0x12: sha2-256 multihash algorithm
      0x20: 32 bytes digest length
    Encoded as RFC 4648 Base32 lowercase prefixed with 'b'.
    """
    digest = hashlib.sha256(data).digest()
    multihash = bytes([0x01, 0x55, 0x12, 0x20]) + digest
    b32 = base64.b32encode(multihash).decode("ascii").rstrip("=").lower()
    return f"b{b32}"

