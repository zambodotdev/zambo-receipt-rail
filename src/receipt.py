"""AER-1 receipt construction for a settled payment.

Builds the canonical receipt payload for one payment record, derives
output_hash as SHA-256 over the canonical bytes, and returns the receipt
object. Verification is done with the published aer1-verify checker against
the receipt's canonical_bytes, the same construction production AER-1
consumers recompute downstream.
"""
import base64
import hashlib
import json


def canonical_bytes(payload: dict) -> bytes:
    """RFC 8785 (JCS) canonical form of the receipt payload."""
    import jcs

    return jcs.canonicalize(payload)


def issue_receipt(*, receipt_id: str, tool: dict, inputs: dict, outputs: dict,
                  caller: str, created_at: str) -> dict:
    payload = {
        "id": receipt_id,
        "tool": tool,
        "inputs": inputs,
        "outputs": outputs,
        "caller": caller,
        "created_at": created_at,
    }
    canon = canonical_bytes(payload)
    return {
        **payload,
        "canonical_bytes": base64.b64encode(canon).decode(),
        "output_hash": "sha256:" + hashlib.sha256(canon).hexdigest(),
    }
