#!/usr/bin/env python3
"""
Headless intake runner.

  # one image, automated draft via local qwen3.6, staged for review (unsigned):
  python cli.py samples/map.png --outdir corpus_staging

  # a whole folder, batch:
  python cli.py samples/ --outdir corpus_staging

  # offline / no Ollama: deterministic mock recognizer
  python cli.py samples/ --backend mock --outdir corpus_staging

  # promote lint-clean results (records your sign-off):
  python cli.py samples/ --backend mock --sign "Anson Parker" --outdir corpus_out

Promotion is refused unless lint is error-free AND --sign is given. Everything
else is written to <outdir>/review/ for a human pass.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys

import pipeline
import provenance as prov
import recognizer as rec

IMG_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


def contributor_from(path, override):
    if override:
        return override
    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r"([A-Za-z0-9_-]+?)_", stem)   # CONTRIB-0007_...  convention
    return (m.group(1) if m else stem)[:40]


def gather(inp):
    if os.path.isdir(inp):
        return sorted(f for f in glob.glob(os.path.join(inp, "*"))
                      if f.lower().endswith(IMG_EXT))
    return [inp]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lexipedia sketch intake (headless)")
    ap.add_argument("input", help="image file or directory of images")
    ap.add_argument("--backend", default="local-vlm",
                    choices=["local-vlm","elca","mock","manual","self-hosted"])
    ap.add_argument("--model", default="qwen3.6")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--endpoint", default="")
    ap.add_argument("--outdir", default="corpus_staging")
    ap.add_argument("--contributor", default="")
    ap.add_argument("--handle", default="")
    ap.add_argument("--display-public", action="store_true")
    ap.add_argument("--known", default="", help="comma-sep known corpus process IDs")
    ap.add_argument("--sign", default="", help="reviewer name; enables promotion of clean maps")
    args = ap.parse_args(argv)

    backend = rec.get_backend(args.backend, model=args.model, host=args.host,
                              endpoint=args.endpoint)
    known = {k.strip() for k in args.known.split(",") if k.strip()} or None
    review_dir = os.path.join(args.outdir, "review")
    os.makedirs(review_dir, exist_ok=True)

    images = gather(args.input)
    if not images:
        print("no images found", file=sys.stderr)
        return 2
    print(f"backend={backend.name} available={backend.available()} "
          f"images={len(images)}\n")

    promoted = staged = 0
    for path in images:
        with open(path, "rb") as f:
            data = f.read()
        res = pipeline.run(data, backend, known_processes=known)
        cid = contributor_from(path, args.contributor)
        s = res.get("lint_summary", {})
        tag = "OK" if res.get("ok") else "REVIEW"
        print(f"[{tag}] {os.path.basename(path)}  nodes={res.get('flow_nodes',0)} "
              f"errors={s.get('errors','?')} warnings={s.get('warnings','?')}")
        for n in res.get("notes", []):
            print(f"        - {n}")

        record = prov.build(
            cid, args.handle, args.display_public,
            source_bytes=data, conditioned_bytes=res.get("conditioned_png", b""),
            bpmn_text=res.get("bpmn", ""), source_filename=os.path.basename(path),
            recognizer_backend=backend.name, condition_report=res.get("condition_report", {}),
            lint_summary=s)

        if args.sign and res.get("ok"):
            paths = prov.promote(args.outdir, record, bpmn_text=res["bpmn"],
                                 conditioned_bytes=res.get("conditioned_png", b""),
                                 signer=args.sign)
            promoted += 1
            print(f"        promoted -> {os.path.basename(paths['bpmn'])}")
        else:
            base = os.path.join(review_dir, f"{cid}_{os.path.splitext(os.path.basename(path))[0]}")
            with open(base + ".draft.bpmn", "w", encoding="utf-8") as f:
                f.write(res.get("bpmn", ""))
            with open(base + ".lint.json", "w", encoding="utf-8") as f:
                json.dump({"summary": s, "findings": res.get("findings", []),
                           "notes": res.get("notes", [])}, f, indent=2)
            staged += 1

    print(f"\ndone: {promoted} promoted, {staged} staged for review in {review_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
