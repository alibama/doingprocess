"""Tiny local HTTP client for the recognizer service (serve_recognize.py).
Pure functions over urllib so they're testable without Streamlit."""
from __future__ import annotations
import json
import urllib.request


def _base(url: str) -> str:
    return url.rstrip("/")


def recognize(base: str, image_bytes: bytes, timeout=180) -> str:
    req = urllib.request.Request(_base(base) + "/recognize", data=image_bytes,
                                 headers={"Content-Type": "application/octet-stream"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def detect(base: str, image_bytes: bytes, timeout=180) -> dict:
    req = urllib.request.Request(_base(base) + "/detect", data=image_bytes,
                                 headers={"Content-Type": "application/octet-stream"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))


def assemble(base: str, payload: dict, timeout=180) -> str:
    req = urllib.request.Request(_base(base) + "/assemble",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")


def health(base: str, timeout=3) -> dict:
    return json.loads(urllib.request.urlopen(_base(base) + "/health", timeout=timeout).read())
