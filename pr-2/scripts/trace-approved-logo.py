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


def interpolate(a: float, b: float, level: float = ISO_LEVEL) -> float:
    if abs(b - a) < 1e-12:
        return 0.5
    return max(0.0, min(1.0, (level - a) / (b - a)))


def marching_segments(field: np.ndarray) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return iso-contour segments using marching squares over pixel centers."""
    height, width = field.shape
    padded = np.zeros((height + 2, width + 2), dtype=np.float64)
    padded[1:-1, 1:-1] = field
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

    for row in range(height + 1):
        for col in range(width + 1):
            tl = padded[row, col]
            tr = padded[row, col + 1]
            br = padded[row + 1, col + 1]
            bl = padded[row + 1, col]
            case = (8 if tl >= ISO_LEVEL else 0) | (4 if tr >= ISO_LEVEL else 0)
            case |= (2 if br >= ISO_LEVEL else 0) | (1 if bl >= ISO_LEVEL else 0)
            if case in (0, 15):
                continue

            x0 = col - 0.5
            y0 = row - 0.5
            points = {
                "T": (x0 + interpolate(tl, tr), y0),
                "R": (x0 + 1.0, y0 + interpolate(tr, br)),
                "B": (x0 + interpolate(bl, br), y0 + 1.0),
                "L": (x0, y0 + interpolate(tl, bl)),
            }
            pairs_by_case = {
                1: (("B", "L"),),
                2: (("R", "B"),),
                3: (("R", "L"),),
                4: (("T", "R"),),
                6: (("T", "B"),),
                7: (("T", "L"),),
                8: (("L", "T"),),
                9: (("B", "T"),),
                11: (("T", "R"),),
                12: (("L", "R"),),
                13: (("R", "B"),),
                14: (("B", "L"),),
            }
            if case in (5, 10):
                center_inside = (tl + tr + br + bl) / 4.0 >= ISO_LEVEL
                if case == 5:
                    pairs = (("T", "L"), ("R", "B")) if center_inside else (("T", "R"), ("B", "L"))
                else:
                    pairs = (("T", "R"), ("B", "L")) if center_inside else (("T", "L"), ("R", "B"))
            else:
                pairs = pairs_by_case[case]
            segments.extend((points[start], points[end]) for start, end in pairs)
    return segments


def point_key(point: tuple[float, float]) -> tuple[int, int]:
    return round(point[0] * 1_000_000), round(point[1] * 1_000_000)


def join_segments(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    adjacency: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, (start, end) in enumerate(segments):
        adjacency[point_key(start)].append(index)
        adjacency[point_key(end)].append(index)

    used: set[int] = set()
    loops: list[list[tuple[float, float]]] = []
    for first_index, (first_start, _first_end) in enumerate(segments):
        if first_index in used:
            continue
        loop = [first_start]
        current_key = point_key(first_start)
        segment_index = first_index
        while segment_index not in used:
            used.add(segment_index)
            start, end = segments[segment_index]
            next_point = end if point_key(start) == current_key else start
            next_key = point_key(next_point)
            loop.append(next_point)
            if next_key == point_key(loop[0]):
                break
            candidates = [candidate for candidate in adjacency[next_key] if candidate not in used]
            if not candidates:
                break
            segment_index = candidates[0]
            current_key = next_key
        if len(loop) >= 4 and point_key(loop[0]) == point_key(loop[-1]):
            loops.append(loop[:-1])
    return loops


def perpendicular_distance(point, start, end) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) + abs(dy) < 1e-12:
        return math.hypot(px - x1, py - y1)
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def rdp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    start = points[0]
    end = points[-1]
    distances = [perpendicular_distance(point, start, end) for point in points[1:-1]]
    if not distances:
        return [start, end]
    maximum = max(distances)
    if maximum <= tolerance:
        return [start, end]
    index = distances.index(maximum) + 1
    left = rdp(points[: index + 1], tolerance)
    right = rdp(points[index:], tolerance)
    return left[:-1] + right


def polygon_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    )


def simplify_closed(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) < 4:
        return points
    anchor = min(range(len(points)), key=lambda index: (points[index][0], points[index][1]))
    ordered = points[anchor:] + points[:anchor]
    ax, ay = ordered[0]
    opposite = max(
        range(1, len(ordered)),
        key=lambda index: (ordered[index][0] - ax) ** 2 + (ordered[index][1] - ay) ** 2,
    )
    first = rdp(ordered[: opposite + 1], tolerance)
    second = rdp(ordered[opposite:] + [ordered[0]], tolerance)
    return first[:-1] + second[:-1]


def fmt(value: float) -> str:
    rounded = round(value, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def path_data(
    loops: list[list[tuple[float, float]]],
    translate: tuple[float, float] = (0.0, 0.0),
) -> str:
    tx, ty = translate
    commands: list[str] = []
    for loop in loops:
        simplified = simplify_closed(loop, SIMPLIFY_TOLERANCE)
        if len(simplified) < 3 or abs(polygon_area(simplified)) < 0.8:
            continue
        points = [(x + tx, y + ty) for x, y in simplified]
        commands.append(f"M{fmt(points[0][0])} {fmt(points[0][1])}")
        commands.extend(f"L{fmt(x)} {fmt(y)}" for x, y in points[1:])
        commands.append("Z")
    return " ".join(commands)


def svg_document(width: int, height: int, title: str, description: str, path: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{description}</desc>
  <path fill="{INK_HEX}" fill-rule="evenodd" d="{path}"/>
</svg>
'''


def trace(source: Path, region: tuple[int, int, int, int] | None = None):
    image = Image.open(source)
    alpha = ink_alpha(image)
    if region is not None:
        left, top, right, bottom = region
        mask = np.zeros_like(alpha)
        mask[top:bottom, left:right] = alpha[top:bottom, left:right]
        alpha = mask
    loops = join_segments(marching_segments(alpha))
    return loops


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("assets"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    mocks = Path("Buddy Brewer Mocks")
    horizontal_loops = trace(mocks / "logo-approved-horizontal.png")
    stacked_loops = trace(mocks / "logo-approved-stacked.png")
    mark_loops = trace(mocks / "logo-approved-stacked.png", (0, 0, 380, 270))

    files = {
        "buddy-brewer-logo-horizontal.svg": svg_document(
            800,
            385,
            "Buddy Brewer horizontal logo",
            "Vector silhouette traced from the approved Buddy Brewer horizontal logo artwork.",
            path_data(horizontal_loops),
        ),
        "buddy-brewer-logo-stacked.svg": svg_document(
            380,
            550,
            "Buddy Brewer stacked logo",
            "Vector silhouette traced from the approved Buddy Brewer stacked logo artwork.",
            path_data(stacked_loops),
        ),
        "buddy-brewer-mark.svg": svg_document(
            260,
            240,
            "Buddy Brewer smile mark",
            "Vector silhouette traced from the smile mark in the approved Buddy Brewer artwork.",
            path_data(mark_loops, (-49.0, -40.0)),
        ),
    }
    for filename, content in files.items():
        destination = args.output_dir / filename
        destination.write_text(content, encoding="utf-8")
        print(destination)


if __name__ == "__main__":
    main()
