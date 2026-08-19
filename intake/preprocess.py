"""
Image conditioning for scanned hand-drawn BPMN maps.

Every step here targets a specific recognition challenge enumerated in
Schaefer et al., "Sketch2Process" (IEEE TSE 2023), Section 3:
  - ruled/graph paper adds false lines (g1)     -> remove_ruled_lines
  - rotation / skew from camera capture         -> deskew
  - pencil / faint strokes, uneven lighting     -> binarize (adaptive)
  - background noise, punch holes, bleed-through -> denoise + autocrop
Local-first: pure OpenCV/NumPy, no network, no cloud OCR.
"""
from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass, field, asdict


@dataclass
class ConditionReport:
    steps: list = field(default_factory=list)
    skew_deg: float = 0.0
    in_shape: tuple = (0, 0)
    out_shape: tuple = (0, 0)

    def dict(self):
        return asdict(self)


def _to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def estimate_skew(gray: np.ndarray) -> float:
    """Estimate small page skew (degrees) from the dominant text/line orientation."""
    inv = cv2.bitwise_not(gray)
    thr = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if len(coords) < 50:
        return 0.0
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # normalise minAreaRect angle to [-45, 45]
    if angle < -45:
        angle = 90 + angle
    if angle > 45:
        angle = angle - 90
    return float(angle)


def deskew(gray: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.2:
        return gray
    h, w = gray.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def remove_ruled_lines(gray: np.ndarray) -> np.ndarray:
    """Suppress long thin horizontal/vertical rules (graph/lined paper, g1).

    Detects lines far longer than a pen stroke and lightens them, leaving
    the hand-drawn strokes intact.
    """
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 25, 15)
    h, w = gray.shape[:2]
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 30), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 30)))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    lines = cv2.dilate(cv2.bitwise_or(horiz, vert),
                       cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    out = gray.copy()
    out[lines > 0] = 255
    return out


def binarize(gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold — robust to uneven lighting / pencil (returns 0/255)."""
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 31, 10)


def autocrop(bw: np.ndarray, pad: int = 24) -> np.ndarray:
    inv = cv2.bitwise_not(bw)
    inv = cv2.medianBlur(inv, 3)
    ys, xs = np.where(inv > 0)
    if len(xs) == 0:
        return bw
    x0, x1 = max(0, xs.min() - pad), min(bw.shape[1], xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(bw.shape[0], ys.max() + pad)
    return bw[y0:y1, x0:x1]


def condition(img: np.ndarray, *, do_deskew=True, do_delined=True,
              do_denoise=True, do_binarize=True, do_autocrop=True):
    """Run the conditioning pipeline. Returns (image, ConditionReport)."""
    rep = ConditionReport(in_shape=tuple(img.shape[:2]))
    g = _to_gray(img); rep.steps.append("grayscale")
    if do_denoise:
        g = cv2.fastNlMeansDenoising(g, None, 7, 7, 21); rep.steps.append("denoise")
    if do_deskew:
        rep.skew_deg = estimate_skew(g)
        g = deskew(g, rep.skew_deg); rep.steps.append(f"deskew({rep.skew_deg:.2f}deg)")
    if do_delined:
        g = remove_ruled_lines(g); rep.steps.append("remove_ruled_lines")
    out = binarize(g) if do_binarize else g
    if do_binarize:
        rep.steps.append("binarize")
    if do_autocrop and do_binarize:
        out = autocrop(out); rep.steps.append("autocrop")
    rep.out_shape = tuple(out.shape[:2])
    return out, rep


def load_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def encode_png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG encode failed")
    return buf.tobytes()
