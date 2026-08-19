"""
Provenance for an intake. Ties a scanned map + its BPMN to a contributor ID
(the stable join key), records the CC0 dedication, and gates promotion on an
explicit human sign-off. Local-first: writes a bundle to disk, no network.

The identity model (from the contributor packet):
  - legal identity  -> lives ONLY in the scanned originals archive, never here
  - contributor_id  -> stable join key for scoring / provenance / merge
  - handle          -> public display, opt-in; may be "" for no public credit
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict, field

SCHEMA = "lexipedia.intake.provenance/1"
LICENSE = "CC0-1.0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Provenance:
    schema: str = SCHEMA
    license: str = LICENSE
    contributor_id: str = ""
    handle: str = ""              # "" => no public credit
    display_public: bool = False
    source_image_sha256: str = ""
    conditioned_image_sha256: str = ""
    bpmn_sha256: str = ""
    source_filename: str = ""
    recognizer_backend: str = "manual"
    condition_report: dict = field(default_factory=dict)
    lint_summary: dict = field(default_factory=dict)
    signed_off_by: str = ""
    signed_off_at: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def dict(self):
        return asdict(self)


def build(contributor_id, handle, display_public, *, source_bytes, conditioned_bytes,
          bpmn_text, source_filename, recognizer_backend, condition_report, lint_summary):
    return Provenance(
        contributor_id=contributor_id.strip(),
        handle=(handle or "").strip(),
        display_public=bool(display_public and (handle or "").strip()),
        source_image_sha256=sha256(source_bytes),
        conditioned_image_sha256=sha256(conditioned_bytes),
        bpmn_sha256=sha256(bpmn_text.encode("utf-8")),
        source_filename=source_filename,
        recognizer_backend=recognizer_backend,
        condition_report=condition_report,
        lint_summary=lint_summary,
    )


def promote(outdir, prov: Provenance, *, bpmn_text, conditioned_bytes, signer):
    """Write the bundle. Refuses without a signer (human sign-off gate)."""
    if not signer or not signer.strip():
        raise PermissionError("human sign-off required before promotion")
    if not prov.contributor_id:
        raise ValueError("contributor_id is required")
    prov.signed_off_by = signer.strip()
    prov.signed_off_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"{prov.contributor_id}_{stamp}"
    os.makedirs(outdir, exist_ok=True)
    bpmn_path = os.path.join(outdir, base + ".bpmn")
    img_path = os.path.join(outdir, base + ".png")
    meta_path = os.path.join(outdir, base + ".provenance.json")
    with open(bpmn_path, "w", encoding="utf-8") as f:
        f.write(bpmn_text)
    with open(img_path, "wb") as f:
        f.write(conditioned_bytes)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(prov.dict(), f, indent=2)
    return {"bpmn": bpmn_path, "image": img_path, "provenance": meta_path}
