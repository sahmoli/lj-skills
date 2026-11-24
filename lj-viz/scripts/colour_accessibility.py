#!/usr/bin/env python3
"""Shared deterministic colour-vision transforms and perceptual distances."""
from __future__ import annotations

import numpy as np

# Severe colour-vision simulations used consistently by numeric and rendered
# review. They are screens, not substitutes for redundant encoding or testing
# with readers.
CVD_MATRICES = {
    "Protanopia": np.array([[0.152, 1.053, -0.205], [0.115, 0.786, 0.099], [-0.004, -0.048, 1.052]]),
    "Deuteranopia": np.array([[0.367, 0.861, -0.228], [0.280, 0.673, 0.047], [-0.012, 0.043, 0.969]]),
    "Tritanopia": np.array([[1.255, -0.077, -0.178], [-0.078, 0.931, 0.148], [0.005, 0.691, 0.304]]),
}

_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
_D65 = np.array([0.95047, 1.0, 1.08883])


def parse_hex(value: str) -> np.ndarray:
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"expected six-digit hex colour: {value}")
    return np.array([int(raw[index:index + 2], 16) for index in (0, 2, 4)], dtype=float) / 255


def srgb_to_linear(encoded: np.ndarray) -> np.ndarray:
    encoded = np.asarray(encoded, dtype=float)
    return np.where(encoded <= 0.04045, encoded / 12.92, ((encoded + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(linear: np.ndarray) -> np.ndarray:
    linear = np.clip(np.asarray(linear, dtype=float), 0, 1)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def simulate_linear(linear: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(linear) @ matrix.T, 0, 1)


def linear_to_lab(linear: np.ndarray) -> np.ndarray:
    values = np.asarray(linear, dtype=float)
    xyz = values @ _XYZ.T
    ratio = xyz / _D65
    delta = 6 / 29
    transformed = np.where(
        ratio > delta ** 3,
        np.cbrt(ratio),
        ratio / (3 * delta ** 2) + 4 / 29,
    )
    return np.stack((
        116 * transformed[..., 1] - 16,
        500 * (transformed[..., 0] - transformed[..., 1]),
        200 * (transformed[..., 1] - transformed[..., 2]),
    ), axis=-1)


def delta_e76(first: str, second: str, matrix: np.ndarray | None = None) -> float:
    a = srgb_to_linear(parse_hex(first))
    b = srgb_to_linear(parse_hex(second))
    if matrix is not None:
        a = simulate_linear(a, matrix)
        b = simulate_linear(b, matrix)
    return float(np.linalg.norm(linear_to_lab(a) - linear_to_lab(b)))
