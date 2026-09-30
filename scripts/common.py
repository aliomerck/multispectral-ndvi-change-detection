import csv
import math
import os
from pathlib import Path

import numpy as np
import rasterio


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def list_tifs(input_dir):
    return sorted(Path(input_dir).glob("*.tif"))


def read_tif(path):
    with rasterio.open(path) as ds:
        data = ds.read()
        profile = ds.profile
        descriptions = ds.descriptions
    return data, profile, descriptions


def write_tif(path, data, profile, dtype=None, descriptions=None):
    out_profile = profile.copy()
    if dtype is None:
        dtype = data.dtype
    out_profile.update(dtype=dtype, count=data.shape[0])
    with rasterio.open(path, "w", **out_profile) as ds:
        for i in range(data.shape[0]):
            ds.write(data[i].astype(dtype), i + 1)
        if descriptions:
            ds.descriptions = tuple(descriptions)


def band_indices_from_descriptions(descriptions):
    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i
    return mapping


def box_filter(img, k):
    if k % 2 == 0:
        raise ValueError("k must be odd")
    pad = k // 2
    padded = np.pad(img, pad_width=pad, mode="reflect")
    cumsum = padded.cumsum(axis=0).cumsum(axis=1)
    cumsum = np.pad(cumsum, ((1, 0), (1, 0)), mode="constant", constant_values=0)
    k2 = k * k
    sum_ = (
        cumsum[k:, k:]
        - cumsum[:-k, k:]
        - cumsum[k:, :-k]
        + cumsum[:-k, :-k]
    )
    return sum_ / k2


def dark_object_subtraction(data, percentile=1.0):
    out = np.empty_like(data, dtype=np.float32)
    for i in range(data.shape[0]):
        band = data[i].astype(np.float32)
        haze = np.percentile(band, percentile)
        band = band - haze
        band[band < 0] = 0
        out[i] = band
    return out


def homomorphic_filter(band, gamma_l=0.5, gamma_h=1.5, c=1.0, d0=30):
    band = band.astype(np.float32)
    max_val = np.percentile(band, 99.9)
    if max_val <= 0:
        return band
    norm = band / max_val
    log_img = np.log1p(norm)

    rows, cols = band.shape
    u = np.arange(rows) - rows / 2.0
    v = np.arange(cols) - cols / 2.0
    U, V = np.meshgrid(u, v, indexing="ij")
    D2 = U * U + V * V
    H = (gamma_h - gamma_l) * (1 - np.exp(-c * D2 / (d0 * d0))) + gamma_l

    fft = np.fft.fftshift(np.fft.fft2(log_img))
    filtered = H * fft
    inv = np.fft.ifft2(np.fft.ifftshift(filtered))
    out = np.expm1(np.real(inv))
    out = out * max_val
    out[out < 0] = 0
    return out.astype(np.float32)


def adaptive_noise_reduction(band, window=7, noise_percentile=10):
    band = band.astype(np.float32)
    mean = box_filter(band, window)
    mean_sq = box_filter(band * band, window)
    var = mean_sq - mean * mean
    var[var < 0] = 0
    noise_var = np.percentile(var, noise_percentile)
    eps = 1e-6
    out = band.copy()
    mask = var > noise_var + eps
    out[mask] = band[mask] - (noise_var / var[mask]) * (band[mask] - mean[mask])
    out[~mask] = mean[~mask]
    out[out < 0] = 0
    return out.astype(np.float32)


def compute_ndvi(red, nir):
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)
    denom = nir + red
    return (nir - red) / (denom + 1e-6)


def compute_hue(red, green, blue, degrees=True):
    r = red.astype(np.float32)
    g = green.astype(np.float32)
    b = blue.astype(np.float32)
    max_val = np.maximum(np.maximum(r, g), b)
    max_val[max_val == 0] = 1
    r = r / max_val
    g = g / max_val
    b = b / max_val

    num = 0.5 * ((r - g) + (r - b))
    den = np.sqrt((r - g) ** 2 + (r - b) * (g - b)) + 1e-6
    theta = np.arccos(np.clip(num / den, -1, 1))
    hue = np.where(b <= g, theta, 2 * math.pi - theta)
    if degrees:
        hue = np.degrees(hue)
    return hue.astype(np.float32)


def write_csv(path, rows, header):
    ensure_dir(Path(path).parent)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
