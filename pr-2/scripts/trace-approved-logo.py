#!/usr/bin/env python3
"""Trace the approved Buddy Brewer PNG lockups into reusable SVG silhouettes."""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


PAPER = np.array([253.0, 248.0, 242.0])
INK = np.array([1.0, 22.0, 53.0])
INK_HEX = "#011635"
ISO_LEVEL = 0.5
SIMPLIFY_TOLERANCE = 0.08


def ink_alpha(image: Image.Image) -> np.ndarray:
    """Estimate ink coverage by projecting RGB pixels onto paper-to-ink color."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    direction = PAPER - INK
    alpha = np.sum((PAPER - rgb) * direction, axis=2) / np.dot(direction, direction)
    return np.clip(alpha, 0.0, 1.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("assets"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print("trace-approved-logo.py present in preview")


if __name__ == "__main__":
    main()
