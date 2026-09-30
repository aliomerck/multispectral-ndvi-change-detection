# EE 475 Final Project Report

## Cover
Title: Multitemporal Vegetation Change Detection with Radiometric Correction and NDVI

Author(s) and ID(s): <NAME 1> (<ID 1>), <NAME 2> (<ID 2>)

Total word count (excluding appendix/code): 1059

## Introduction
This project implements a complete multitemporal image-processing pipeline to analyze vegetation
change using multispectral satellite imagery. The pipeline combines radiometric correction,
illumination normalization, adaptive noise reduction, and feature extraction (NDVI and hue) to
produce change maps for urban scenes. The primary contribution is an end-to-end, reproducible
workflow that outputs NDVI change maps and vegetation-loss/gain masks while preserving the
GeoTIFF georeferencing for further GIS analysis. We focus on transparent, modular processing so
that each step can be inspected and tuned (e.g., DOS percentile, homomorphic filtering parameters,
noise model, NDVI thresholds), which is important for repeatable environmental monitoring.

The overall approach follows classical digital image processing formulations from Gonzalez and
Woods, especially for illumination-reflectance separation, homomorphic filtering, and adaptive
local noise reduction, and adapts them to remote-sensing indices such as NDVI and NDWI.

Remote sensing change detection is especially sensitive to illumination shifts, haze, and sensor
variability between acquisition dates. By explicitly modeling low-frequency illumination and
reducing variance-driven noise, the pipeline aims to minimize false change that can arise from
non-surface effects. At the same time, the workflow preserves band-level information so that
domain indices (NDVI/NDWI) and color-space features can be derived directly from corrected data.
This combination provides a practical balance between classic image-processing theory and
application-driven spectral analysis.

## Methods and Materials
### Data
Input imagery consists of multispectral GeoTIFFs in `photos/`, named `City_YYYY_*.tif` and
typically containing Sentinel-like bands with descriptions `B2` (blue), `B3` (green), `B4` (red),
`B8` (NIR). The `scripts/01_data_check.py` tool extracts metadata and band descriptions to
validate inputs.

### Processing pipeline
For the reported results, we use Method 1: Raw → DOS → Homomorphic → Denoise → NDVI.
1) **Dark Object Subtraction (DOS)**: For each band, the dark-object percentile is subtracted to
   reduce haze and atmospheric path radiance. This is implemented as
   `band = max(band - percentile(band), 0)`.

2) **Homomorphic filtering** (Gonzalez & Woods): We use the standard illumination-reflectance
   model `f(x,y) = i(x,y) * r(x,y)`. Taking logs yields `ln f = ln i + ln r`, which separates
   low-frequency illumination from high-frequency reflectance. In the frequency domain we apply
   a high-boost filter
   `H(u,v) = (gamma_h - gamma_l) * (1 - exp(-c * D(u,v)^2 / D0^2)) + gamma_l`,
   then exponentiate to recover the image. This corresponds to `scripts/03_homomorphic_filter.py`.

3) **Adaptive local noise reduction** (Gonzalez & Woods): A local-statistics filter suppresses
   noise while preserving edges. The estimate is
   `f_hat(x,y) = g(x,y) - (sigma_n^2 / sigma_L^2) * (g(x,y) - m_L)`,
   where `m_L` and `sigma_L^2` are local mean and variance, and `sigma_n^2` is estimated from a
   low-variance percentile. Implemented in `scripts/04_adaptive_noise_reduction.py`.

4) **Feature extraction**: NDVI and hue are computed from the denoised bands. NDVI is
   `NDVI = (NIR - Red) / (NIR + Red + eps)`. Hue is computed from normalized RGB to capture
   color information complementary to NDVI. Implemented in `scripts/05_features.py`.

5) **K-means segmentation** (Gonzalez & Woods): NDVI and hue vectors are clustered into `k`
   classes using Euclidean distance and iterative centroid updates to minimize within-class
   variance. Implemented in `scripts/06_kmeans_segmentation.py`.

6) **Temporal analysis**: For each city, we compute vegetation masks using NDVI thresholds and
   optional band-ratio constraints. Water pixels are masked using NDWI
   `NDWI = (Green - NIR) / (Green + NIR + eps)` to avoid confusion with vegetation. The output is
   a categorical change map (loss/gain) and a CSV summary. Implemented in
   `scripts/07_temporal_analysis.py`.

7) **NDVI difference maps**: The NDVI difference `NDVI_2024 - NDVI_2016` is computed and
   visualized with a diverging colormap, implemented in `scripts/09_ndvi_colormap_diff.py`.

### Performance metrics
We report (1) mean NDVI per year and mean NDVI difference, and (2) vegetation percentage
per year after applying NDVI, NDWI, and band-ratio masks. These provide interpretable summaries
for change detection and allow comparison across years.

## Results
For Istanbul (2016 vs 2024), the NDVI statistics from Method 1 outputs are:

```
city,year_or_diff,mean_ndvi
Istanbul,2016,0.3757
Istanbul,2024,0.3779
Istanbul,2024-2016,0.0021
```

Vegetation percentage estimates based on NDVI + NDWI + ratio masking are:

```
city,year_a,year_b,veg_pct_a,veg_pct_b,delta_pct
Istanbul,2016,2024,27.58,25.87,-1.71
Istanbul,2024,2016,25.87,27.58,1.71
```

### Figures
Figure 1: NDVI map (2016) for Istanbul.

![Istanbul 2016 NDVI](outputs/istanbul_png_m1/Istanbul_2016_ndvi.png)

Figure 2: NDVI map (2024) for Istanbul.

![Istanbul 2024 NDVI](outputs/istanbul_png_m1/Istanbul_2024_ndvi.png)

Figure 3: NDVI difference map (2024 - 2016) for Istanbul.

![Istanbul NDVI diff](outputs/istanbul_ndvi_diff_m1/Istanbul_ndvi_diff_2024_2016.png)

## Discussion
The mean NDVI increase in Istanbul indicates slightly greener conditions in 2024 compared to
2016, yet the vegetation-percentage metric shows a small decrease when using stricter masks that
also incorporate band ratios and NDWI-based water removal. This discrepancy is expected: mean
NDVI is sensitive to overall greenness, while the vegetation mask emphasizes pixels that satisfy
multiple spectral criteria. The combination of homomorphic filtering and adaptive noise reduction
improved local contrast and reduced low-frequency illumination artifacts, which is critical for
temporal comparison. The DOS step also stabilizes the baseline radiometry across images.

Limitations include the lack of explicit atmospheric correction and the assumption that band
descriptions are consistent across all images. Histogram matching (implemented in
`step11_radiometric_normalization`) can further reduce inter-year radiometric differences, but
was not applied in all runs. Finally, NDVI and NDWI are sensitive to sensor differences and
acquisition geometry, so results should be interpreted with those caveats in mind.

Parameter sensitivity is another consideration. The NDVI threshold and local noise window size
shift the vegetation masks, while the homomorphic filter parameters (gamma values and cutoff
frequency) trade contrast enhancement for potential amplification of artifacts. K-means results
also depend on sampling and initialization, so segmentation outputs are best used as exploratory
visualization rather than strict classification. Future validation against labeled land-cover data
would enable quantitative tuning of these parameters.

## Conclusion
We developed a modular pipeline for multitemporal vegetation change detection using
Gonzalez-and-Woods formulations for illumination/reflection separation and adaptive noise
reduction. The pipeline produces NDVI difference maps and categorical vegetation change masks
from raw GeoTIFF inputs. Future work will incorporate full atmospheric correction, improved
cloud/water masking, and calibration across sensors to strengthen inter-year comparability.

## Bibliography
- R. C. Gonzalez and R. E. Woods, *Digital Image Processing*, 4th ed., Pearson, 2018.
- J. W. Rouse, R. H. Haas, J. A. Schell, and D. W. Deering, "Monitoring vegetation systems in the
  Great Plains with ERTS," NASA SP-351, 1974.
- S. K. McFeeters, "The use of the Normalized Difference Water Index (NDWI) in the delineation
  of open water features," *International Journal of Remote Sensing*, 17(7), 1996.

## Appendix A: Python code

### scripts/common.py

```python
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
```

### scripts/01_data_check.py

```python
import argparse
from pathlib import Path

import rasterio

from common import list_tifs, write_csv


def main():
    parser = argparse.ArgumentParser(description="Scan GeoTIFFs and report metadata.")
    parser.add_argument("--input", default="photos", help="Input folder with .tif files")
    parser.add_argument("--out", default="outputs/00_data_check.csv", help="CSV output path")
    args = parser.parse_args()

    rows = []
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        with rasterio.open(path) as ds:
            names = [n if n else "" for n in ds.descriptions]
            row = [
                path.name,
                ds.width,
                ds.height,
                ds.count,
                str(ds.crs) if ds.crs else "",
                ",".join(ds.dtypes),
                ",".join(names),
            ]
            rows.append(row)
            print(
                f"{path.name}: {ds.width}x{ds.height}, bands={ds.count}, "
                f"dtypes={ds.dtypes}, names={names}"
            )

    write_csv(args.out, rows, ["file", "width", "height", "bands", "crs", "dtypes", "band_names"])
    print("Wrote", Path(args.out))


if __name__ == "__main__":
    main()
```

### scripts/02_dark_object_subtraction.py

```python
import argparse
from pathlib import Path

from common import dark_object_subtraction, ensure_dir, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply Dark Object Subtraction.")
    parser.add_argument("--input", default="photos", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/01_dos", help="Output folder")
    parser.add_argument("--percentile", type=float, default=1.0, help="Dark pixel percentile")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        out = dark_object_subtraction(data, percentile=args.percentile)
        out_path = Path(args.output) / f"{path.stem}_dos.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/03_homomorphic_filter.py

```python
import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, homomorphic_filter, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply homomorphic filtering.")
    parser.add_argument("--input", default="outputs/01_dos", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/02_homomorphic", help="Output folder")
    parser.add_argument("--gamma-l", type=float, default=0.5, help="Low-frequency gain")
    parser.add_argument("--gamma-h", type=float, default=1.5, help="High-frequency gain")
    parser.add_argument("--c", type=float, default=1.0, help="Filter sharpness")
    parser.add_argument("--d0", type=float, default=30.0, help="Cutoff frequency")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        out = []
        for i in range(data.shape[0]):
            out.append(
                homomorphic_filter(
                    data[i],
                    gamma_l=args.gamma_l,
                    gamma_h=args.gamma_h,
                    c=args.c,
                    d0=args.d0,
                )
            )
        out = np.stack(out, axis=0)
        out_path = Path(args.output) / f"{path.stem}_homo.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/04_adaptive_noise_reduction.py

```python
import argparse
from pathlib import Path

import numpy as np

from common import adaptive_noise_reduction, ensure_dir, list_tifs, read_tif, write_tif


def main():
    parser = argparse.ArgumentParser(description="Apply adaptive local noise reduction.")
    parser.add_argument("--input", default="outputs/02_homomorphic", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/03_denoised", help="Output folder")
    parser.add_argument("--window", type=int, default=7, help="Window size (odd)")
    parser.add_argument(
        "--noise-percentile",
        type=float,
        default=10.0,
        help="Percentile for estimating noise variance",
    )
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        out = []
        for i in range(data.shape[0]):
            out.append(
                adaptive_noise_reduction(
                    data[i], window=args.window, noise_percentile=args.noise_percentile
                )
            )
        out = np.stack(out, axis=0)
        out_path = Path(args.output) / f"{path.stem}_denoise.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/05_features.py

```python
import argparse
from pathlib import Path

import numpy as np

from common import (
    band_indices_from_descriptions,
    compute_hue,
    compute_ndvi,
    ensure_dir,
    list_tifs,
    read_tif,
    write_tif,
)


def main():
    parser = argparse.ArgumentParser(description="Compute NDVI and Hue features.")
    parser.add_argument("--input", default="outputs/03_denoised", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/04_features", help="Output folder")
    parser.add_argument("--blue", default="B2", help="Blue band name")
    parser.add_argument("--green", default="B3", help="Green band name")
    parser.add_argument("--red", default="B4", help="Red band name")
    parser.add_argument("--nir", default="B8", help="NIR band name")
    parser.add_argument("--hue-rad", action="store_true", help="Store hue in radians")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        mapping = band_indices_from_descriptions(descriptions)
        try:
            b_i = mapping[args.blue] - 1
            g_i = mapping[args.green] - 1
            r_i = mapping[args.red] - 1
            n_i = mapping[args.nir] - 1
        except KeyError:
            b_i, g_i, r_i, n_i = 0, 1, 2, 3

        blue = data[b_i]
        green = data[g_i]
        red = data[r_i]
        nir = data[n_i]

        ndvi = compute_ndvi(red, nir)
        hue = compute_hue(red, green, blue, degrees=not args.hue_rad)
        out = np.stack([ndvi, hue], axis=0)
        out_path = Path(args.output) / f"{path.stem}_features.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=["NDVI", "HUE"])
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/06_kmeans_segmentation.py

```python
import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_tif


def initialize_centers(features, k, seed=0):
    rng = np.random.default_rng(seed)
    ndvi = features[:, 0]
    hue = features[:, 1]
    p10, p50, p90 = np.percentile(ndvi, [10, 50, 90])
    h50 = np.percentile(hue, 50)
    centers = np.array([[p10, h50], [p50, h50], [p90, h50]], dtype=np.float32)
    if k != 3:
        idx = rng.choice(features.shape[0], size=k, replace=False)
        centers = features[idx].astype(np.float32)
    return centers


def kmeans(features, k=3, iterations=10, seed=0):
    centers = initialize_centers(features, k, seed=seed)
    for _ in range(iterations):
        dists = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1)
        for i in range(k):
            mask = labels == i
            if np.any(mask):
                centers[i] = features[mask].mean(axis=0)
    return labels, centers


def main():
    parser = argparse.ArgumentParser(description="K-means segmentation on NDVI and Hue.")
    parser.add_argument("--input", default="outputs/04_features", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/05_segments", help="Output folder")
    parser.add_argument("--k", type=int, default=3, help="Number of clusters")
    parser.add_argument("--iterations", type=int, default=10, help="K-means iterations")
    parser.add_argument("--sample", type=int, default=200000, help="Sample size for fitting")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        data, profile, descriptions = read_tif(path)
        ndvi = data[0].astype(np.float32)
        hue = data[1].astype(np.float32)
        flat = np.stack([ndvi.ravel(), hue.ravel()], axis=1)
        mask = np.isfinite(flat).all(axis=1)
        flat = flat[mask]

        if flat.shape[0] > args.sample:
            rng = np.random.default_rng(args.seed)
            idx = rng.choice(flat.shape[0], size=args.sample, replace=False)
            sample = flat[idx]
        else:
            sample = flat

        mean = sample.mean(axis=0)
        std = sample.std(axis=0)
        std[std == 0] = 1
        sample_n = (sample - mean) / std

        labels_s, centers = kmeans(sample_n, k=args.k, iterations=args.iterations, seed=args.seed)
        centers = centers * std + mean

        flat_n = (flat - mean) / std
        dists = ((flat_n[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1).astype(np.uint8)

        full_labels = np.zeros(ndvi.size, dtype=np.uint8)
        full_labels[mask] = labels + 1
        label_img = full_labels.reshape(ndvi.shape)
        out = np.expand_dims(label_img, axis=0)

        out_path = Path(args.output) / f"{path.stem}_segments.tif"
        write_tif(out_path, out, profile, dtype="uint8", descriptions=["SEGMENTS"])
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/07_temporal_analysis.py

```python
import argparse
import re
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_csv, write_tif


def parse_city_year(name):
    base = name
    for suffix in ["_dos", "_homo", "_denoise", "_features", "_segments"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", base)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def compute_ndwi(green, nir):
    green = green.astype(np.float32)
    nir = nir.astype(np.float32)
    denom = green + nir
    return (green - nir) / (denom + 1e-6)


def band_indices_from_descriptions(descriptions):
    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i
    return mapping


def load_bands(denoised_path):
    data, _, descriptions = read_tif(denoised_path)
    mapping = band_indices_from_descriptions(descriptions)
    try:
        b_i = mapping["B2"] - 1
        g_i = mapping["B3"] - 1
        r_i = mapping["B4"] - 1
        n_i = mapping["B8"] - 1
    except KeyError:
        b_i, g_i, r_i, n_i = 0, 1, 2, 3
    blue = data[b_i].astype(np.float32)
    green = data[g_i].astype(np.float32)
    red = data[r_i].astype(np.float32)
    nir = data[n_i].astype(np.float32)
    return blue, green, red, nir


def main():
    parser = argparse.ArgumentParser(description="Temporal vegetation change analysis.")
    parser.add_argument("--features", default="outputs/04_features", help="Features folder")
    parser.add_argument("--features-2016", default=None, help="Override 2016 features folder")
    parser.add_argument("--features-2024", default=None, help="Override 2024 features folder")
    parser.add_argument(
        "--bands",
        default="outputs/03_denoised",
        help="Folder containing band data for NDWI/ratios",
    )
    parser.add_argument("--output", default="outputs/06_temporal", help="Output folder")
    parser.add_argument(
        "--ndvi-threshold",
        type=float,
        default=0.3,
        help="NDVI threshold for vegetation mask",
    )
    parser.add_argument(
        "--ndvi-max",
        type=float,
        default=None,
        help="Optional max NDVI for vegetation mask",
    )
    parser.add_argument(
        "--green-red-ratio",
        type=float,
        default=1.05,
        help="Green/Red ratio threshold for vegetation mask",
    )
    parser.add_argument(
        "--nir-red-ratio",
        type=float,
        default=1.2,
        help="NIR/Red ratio threshold for vegetation mask",
    )
    parser.add_argument(
        "--ndwi-threshold",
        type=float,
        default=0.0,
        help="NDWI threshold for water mask (water if NDWI > threshold)",
    )
    parser.add_argument(
        "--land-intersection",
        action="store_true",
        help="Use land mask intersection for both years",
    )
    args = parser.parse_args()

    ensure_dir(args.output)
    feat_files = list_tifs(args.features)
    if not feat_files and not (args.features_2016 or args.features_2024):
        print("Missing feature files.")
        return

    feat_map = {}
    for path in feat_files:
        city, year = parse_city_year(path.stem)
        if city and year:
            feat_map[(city, year)] = path

    if args.features_2016:
        for path in list_tifs(args.features_2016):
            city, year = parse_city_year(path.stem)
            if city and year == 2016:
                feat_map[(city, year)] = path

    if args.features_2024:
        for path in list_tifs(args.features_2024):
            city, year = parse_city_year(path.stem)
            if city and year == 2024:
                feat_map[(city, year)] = path

    rows = []
    for (city, year), feat_path in feat_map.items():
        other_year = 2024 if year == 2016 else 2016
        key_other = (city, other_year)
        if key_other not in feat_map:
            continue

        feat1, profile, _ = read_tif(feat_path)
        feat2, _, _ = read_tif(feat_map[key_other])

        ndvi1 = feat1[0]
        ndvi2 = feat2[0]

        base1 = feat_path.stem.replace("_features", "")
        base2 = feat_map[key_other].stem.replace("_features", "")
        bands1 = Path(args.bands) / f"{base1}.tif"
        bands2 = Path(args.bands) / f"{base2}.tif"
        if bands1.exists() and bands2.exists():
            b1, g1, r1, n1 = load_bands(bands1)
            b2, g2, r2, n2 = load_bands(bands2)
            ndwi1 = compute_ndwi(g1, n1)
            ndwi2 = compute_ndwi(g2, n2)
            water1 = ndwi1 > args.ndwi_threshold
            water2 = ndwi2 > args.ndwi_threshold
        else:
            water1 = np.zeros(ndvi1.shape, dtype=bool)
            water2 = np.zeros(ndvi2.shape, dtype=bool)
            b1 = g1 = r1 = n1 = None
            b2 = g2 = r2 = n2 = None

        land1 = ~water1
        land2 = ~water2
        if args.land_intersection:
            land1 = land1 & land2
            land2 = land1

        veg1 = (ndvi1 > args.ndvi_threshold) & land1
        veg2 = (ndvi2 > args.ndvi_threshold) & land2
        if args.ndvi_max is not None:
            veg1 &= ndvi1 <= args.ndvi_max
            veg2 &= ndvi2 <= args.ndvi_max
        if r1 is not None:
            gr1 = g1 / (r1 + 1e-6)
            nr1 = n1 / (r1 + 1e-6)
            veg1 &= (gr1 > args.green_red_ratio) & (nr1 > args.nir_red_ratio)
        if r2 is not None:
            gr2 = g2 / (r2 + 1e-6)
            nr2 = n2 / (r2 + 1e-6)
            veg2 &= (gr2 > args.green_red_ratio) & (nr2 > args.nir_red_ratio)

        total1 = land1.sum()
        total2 = land2.sum()
        pct1 = float(veg1.sum()) / max(total1, 1) * 100.0
        pct2 = float(veg2.sum()) / max(total2, 1) * 100.0
        delta = pct2 - pct1

        rows.append([city, year, other_year, f"{pct1:.2f}", f"{pct2:.2f}", f"{delta:.2f}"])

        diff = np.zeros(veg1.shape, dtype=np.int8)
        diff[(veg1) & (~veg2)] = -1
        diff[(~veg1) & (veg2)] = 1
        diff[water1 & water2] = 0
        diff_path = Path(args.output) / f"{city}_{year}_{other_year}_veg_diff.tif"
        write_tif(diff_path, diff[np.newaxis, :, :], profile, dtype="int8", descriptions=["VEG_DIFF"])
        print("Wrote", diff_path)

    out_csv = Path(args.output) / "summary.csv"
    write_csv(
        out_csv,
        rows,
        ["city", "year_a", "year_b", "veg_pct_a", "veg_pct_b", "delta_pct"],
    )
    print("Wrote", out_csv)


if __name__ == "__main__":
    main()
```

### scripts/08_export_pngs.py

```python
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio


def scale_to_uint8(arr, p_low=2, p_high=98):
    arr = arr.astype(np.float32)
    if not np.isfinite(arr).any():
        return np.zeros(arr.shape, dtype=np.uint8)
    vmin, vmax = np.percentile(arr[np.isfinite(arr)], [p_low, p_high])
    if vmax <= vmin:
        vmax = vmin + 1.0
    out = (arr - vmin) / (vmax - vmin)
    out = np.clip(out, 0, 1)
    return (out * 255).astype(np.uint8)


def save_rgb(path, r, g, b):
    rgb = np.stack([r, g, b], axis=2)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(path)


def save_gray(path, band):
    img = Image.fromarray(band, mode="L")
    img.save(path)


def export_tif(tif_path, out_dir):
    with rasterio.open(tif_path) as ds:
        data = ds.read()
        descriptions = ds.descriptions

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = tif_path.stem
    count = data.shape[0]

    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i - 1

    if count >= 3 and {"B2", "B3", "B4"}.issubset(mapping):
        b = scale_to_uint8(data[mapping["B2"]])
        g = scale_to_uint8(data[mapping["B3"]])
        r = scale_to_uint8(data[mapping["B4"]])
        save_rgb(out_dir / f"{stem}_rgb.png", r, g, b)
    elif count >= 3:
        r = scale_to_uint8(data[0])
        g = scale_to_uint8(data[1])
        b = scale_to_uint8(data[2])
        save_rgb(out_dir / f"{stem}_rgb.png", r, g, b)

    if count == 1:
        band = scale_to_uint8(data[0])
        save_gray(out_dir / f"{stem}.png", band)
    elif count == 2:
        name1 = descriptions[0] if descriptions[0] else "band1"
        name2 = descriptions[1] if descriptions[1] else "band2"
        save_gray(out_dir / f"{stem}_{name1.lower()}.png", scale_to_uint8(data[0]))
        save_gray(out_dir / f"{stem}_{name2.lower()}.png", scale_to_uint8(data[1]))
    elif count > 3:
        for i in range(count):
            name = descriptions[i] if descriptions[i] else f"band{i+1}"
            save_gray(out_dir / f"{stem}_{name.lower()}.png", scale_to_uint8(data[i]))


def main():
    parser = argparse.ArgumentParser(description="Export GeoTIFFs to PNG quicklooks.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--output", default="outputs/png", help="PNG output folder")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_root = root / args.output

    tif_paths = []
    for folder in ["photos", "outputs"]:
        path = root / folder
        if path.exists():
            tif_paths.extend(path.rglob("*.tif"))

    if not tif_paths:
        print("No .tif files found.")
        return

    for tif_path in tif_paths:
        rel = tif_path.parent.relative_to(root)
        out_dir = out_root / rel
        export_tif(tif_path, out_dir)
        print("Exported", tif_path.name, "->", out_dir)


if __name__ == "__main__":
    main()
```

### scripts/09_ndvi_colormap_diff.py

```python
import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image

from common import ensure_dir, list_tifs, read_tif, write_csv, write_tif


def parse_city_year(name):
    base = name
    for suffix in ["_features"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", base)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def ndvi_colormap(ndvi):
    x = np.clip((ndvi + 1.0) / 2.0, 0, 1)
    # Red (-1) -> Yellow (0) -> Green (+1)
    r = np.where(x < 0.5, 1.0, 1.0 - (x - 0.5) * 2.0)
    g = np.where(x < 0.5, x * 2.0, 1.0)
    b = np.zeros_like(x)
    rgb = np.stack([r, g, b], axis=2)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def diff_colormap(diff, vmin=-0.5, vmax=0.5):
    x = (diff - vmin) / (vmax - vmin)
    x = np.clip(x, 0, 1)
    r = np.where(x > 0.5, (x - 0.5) * 2.0, 0.0)
    b = np.where(x < 0.5, (0.5 - x) * 2.0, 0.0)
    g = 1.0 - (np.abs(x - 0.5) * 2.0)
    rgb = np.stack([r, g, b], axis=2)
    return (rgb * 255).astype(np.uint8)


def save_png(path, rgb):
    Image.fromarray(rgb, mode="RGB").save(path)


def main():
    parser = argparse.ArgumentParser(description="NDVI colormap and year-to-year diff.")
    parser.add_argument("--features", default="outputs/04_features", help="Features folder")
    parser.add_argument("--out-ndvi", default="outputs/07_ndvi_png", help="NDVI PNG folder")
    parser.add_argument("--out-diff", default="outputs/08_ndvi_diff", help="NDVI diff outputs")
    args = parser.parse_args()

    features = list_tifs(args.features)
    if not features:
        print("No feature .tif files found.")
        return

    out_ndvi = Path(args.out_ndvi)
    out_diff = Path(args.out_diff)
    ensure_dir(out_ndvi)
    ensure_dir(out_diff)

    by_city_year = {}
    for path in features:
        city, year = parse_city_year(path.stem)
        if city and year:
            by_city_year[(city, year)] = path

    stats = []
    for (city, year), feat_path in by_city_year.items():
        data, profile, _ = read_tif(feat_path)
        ndvi = data[0].astype(np.float32)
        rgb = ndvi_colormap(ndvi)
        out_path = out_ndvi / f"{city}_{year}_ndvi.png"
        save_png(out_path, rgb)
        stats.append([city, year, f"{float(np.nanmean(ndvi)):.4f}"])

    for city in set(c for c, _ in by_city_year.keys()):
        if (city, 2016) in by_city_year and (city, 2024) in by_city_year:
            ndvi16, profile, _ = read_tif(by_city_year[(city, 2016)])
            ndvi24, _, _ = read_tif(by_city_year[(city, 2024)])
            diff = (ndvi24[0].astype(np.float32) - ndvi16[0].astype(np.float32))
            diff_tif = out_diff / f"{city}_ndvi_diff_2024_2016.tif"
            write_tif(diff_tif, diff[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI_DIFF"])
            diff_png = out_diff / f"{city}_ndvi_diff_2024_2016.png"
            save_png(diff_png, diff_colormap(diff))
            stats.append([city, "2024-2016", f"{float(np.nanmean(diff)):.4f}"])

    write_csv(out_diff / "ndvi_stats.csv", stats, ["city", "year_or_diff", "mean_ndvi"])
    print("Wrote NDVI PNGs to", out_ndvi)
    print("Wrote NDVI diffs to", out_diff)


if __name__ == "__main__":
    main()
```

### scripts/10_color_istanbul_diff.py

```python
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio


def main():
    parser = argparse.ArgumentParser(description="Colorize Istanbul vegetation diff.")
    parser.add_argument(
        "--input",
        default="outputs/06_temporal/Istanbul_2016_2024_veg_diff.tif",
        help="Input diff TIFF (2016_2024 order)",
    )
    parser.add_argument(
        "--output",
        default="outputs/06_temporal/Istanbul_veg_change_red_yellow.png",
        help="Output PNG path",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Missing diff file: {in_path}")

    with rasterio.open(in_path) as ds:
        diff = ds.read(1)

    # For 2016_2024 order: -1 => loss, +1 => gain.
    h, w = diff.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    loss = diff == -1
    gain = diff == 1

    rgb[loss] = (255, 0, 0)     # red = loss
    rgb[gain] = (255, 255, 0)   # yellow = gain

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, mode="RGB").save(out_path)
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/11_radiometric_normalization.py

```python
import argparse
import re
from pathlib import Path

import numpy as np

from common import ensure_dir, list_tifs, read_tif, write_tif


def parse_city_year(name):
    match = re.match(r"^(?P<city>.+)_(?P<year>\d{4})_", name)
    if not match:
        return None, None
    return match.group("city"), int(match.group("year"))


def match_histogram_quantiles(source, reference, quantiles=1024):
    src = source.astype(np.float32)
    ref = reference.astype(np.float32)
    mask_src = np.isfinite(src)
    mask_ref = np.isfinite(ref)
    if not mask_src.any() or not mask_ref.any():
        return src

    qs = np.linspace(0.0, 1.0, quantiles)
    src_q = np.quantile(src[mask_src], qs)
    ref_q = np.quantile(ref[mask_ref], qs)

    # Ensure monotonicity for interpolation
    src_q = np.maximum.accumulate(src_q)
    ref_q = np.maximum.accumulate(ref_q)

    flat = src.ravel()
    matched = np.interp(flat, src_q, ref_q).reshape(src.shape)
    return matched.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Radiometric normalization via histogram matching.")
    parser.add_argument("--input", default="outputs/01_dos", help="Input folder (DOS outputs)")
    parser.add_argument("--output", default="outputs/01_dos_norm", help="Output folder")
    parser.add_argument("--quantiles", type=int, default=1024, help="Quantiles for matching")
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    by_city_year = {}
    for path in files:
        city, year = parse_city_year(path.stem)
        if city and year:
            by_city_year[(city, year)] = path

    for (city, year), src_path in by_city_year.items():
        if year != 2024:
            continue
        ref_key = (city, 2016)
        if ref_key not in by_city_year:
            continue

        ref_path = by_city_year[ref_key]
        src_data, profile, descriptions = read_tif(src_path)
        ref_data, _, _ = read_tif(ref_path)

        out = np.empty_like(src_data, dtype=np.float32)
        for i in range(src_data.shape[0]):
            out[i] = match_histogram_quantiles(
                src_data[i], ref_data[i], quantiles=args.quantiles
            )

        out_path = Path(args.output) / f"{src_path.stem}_norm.tif"
        write_tif(out_path, out, profile, dtype="float32", descriptions=descriptions)
        print("Wrote", out_path)


if __name__ == "__main__":
    main()
```

### scripts/12_radiometric_normalization_pair.py

```python
import argparse
from pathlib import Path

import numpy as np

from common import ensure_dir, read_tif, write_tif


def match_histogram_quantiles(source, reference, quantiles=1024):
    src = source.astype(np.float32)
    ref = reference.astype(np.float32)
    mask_src = np.isfinite(src)
    mask_ref = np.isfinite(ref)
    if not mask_src.any() or not mask_ref.any():
        return src

    qs = np.linspace(0.0, 1.0, quantiles)
    src_q = np.quantile(src[mask_src], qs)
    ref_q = np.quantile(ref[mask_ref], qs)

    src_q = np.maximum.accumulate(src_q)
    ref_q = np.maximum.accumulate(ref_q)

    flat = src.ravel()
    matched = np.interp(flat, src_q, ref_q).reshape(src.shape)
    return matched.astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Normalize 2016 and 2024 to a common histogram.")
    parser.add_argument("--ref-2016", required=True, help="2016 DOS TIFF")
    parser.add_argument("--ref-2024", required=True, help="2024 DOS TIFF")
    parser.add_argument("--output", default="outputs/01_dos_norm_pair", help="Output folder")
    parser.add_argument("--quantiles", type=int, default=1024, help="Quantiles for matching")
    args = parser.parse_args()

    ensure_dir(args.output)
    p16 = Path(args.ref_2016)
    p24 = Path(args.ref_2024)

    d16, profile, desc = read_tif(p16)
    d24, _, _ = read_tif(p24)

    out16 = np.empty_like(d16, dtype=np.float32)
    out24 = np.empty_like(d24, dtype=np.float32)

    for i in range(d16.shape[0]):
        band16 = d16[i]
        band24 = d24[i]
        ref_q = (band16.astype(np.float32) + band24.astype(np.float32)) / 2.0
        out16[i] = match_histogram_quantiles(band16, ref_q, quantiles=args.quantiles)
        out24[i] = match_histogram_quantiles(band24, ref_q, quantiles=args.quantiles)

    out16_path = Path(args.output) / f"{p16.stem}_normpair.tif"
    out24_path = Path(args.output) / f"{p24.stem}_normpair.tif"
    write_tif(out16_path, out16, profile, dtype="float32", descriptions=desc)
    write_tif(out24_path, out24, profile, dtype="float32", descriptions=desc)
    print("Wrote", out16_path)
    print("Wrote", out24_path)


if __name__ == "__main__":
    main()
```

### scripts/13_run_ndvi_diff_pipeline.py

```python
﻿import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from common import (
    adaptive_noise_reduction,
    band_indices_from_descriptions,
    compute_ndvi,
    dark_object_subtraction,
    ensure_dir,
    homomorphic_filter,
    read_tif,
    write_tif,
)


def ndvi_colormap(ndvi):
    x = np.clip((ndvi + 1.0) / 2.0, 0, 1)
    r = np.where(x < 0.5, 1.0, 1.0 - (x - 0.5) * 2.0)
    g = np.where(x < 0.5, x * 2.0, 1.0)
    b = np.zeros_like(x)
    rgb = np.stack([r, g, b], axis=2)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def diff_colormap(diff, vmin=-0.5, vmax=0.5):
    x = (diff - vmin) / (vmax - vmin)
    x = np.clip(x, 0, 1)
    r = np.where(x > 0.5, (x - 0.5) * 2.0, 0.0)
    b = np.where(x < 0.5, (0.5 - x) * 2.0, 0.0)
    g = 1.0 - (np.abs(x - 0.5) * 2.0)
    rgb = np.stack([r, g, b], axis=2)
    return (rgb * 255).astype(np.uint8)


def save_png(path, rgb):
    Image.fromarray(rgb, mode="RGB").save(path)


def resolve_band_indices(descriptions, blue, green, red, nir):
    mapping = band_indices_from_descriptions(descriptions)

    def idx(name, fallback):
        if name in mapping:
            return mapping[name] - 1
        return fallback

    return (
        idx(blue, 0),
        idx(green, 1),
        idx(red, 2),
        idx(nir, 3),
    )


def process_image(path, args, out_dir, prefix):
    data, profile, descriptions = read_tif(path)

    dos = dark_object_subtraction(data, percentile=args.dos_percentile)
    dos_path = out_dir / f"{prefix}_dos.tif"
    write_tif(dos_path, dos, profile, dtype="float32", descriptions=descriptions)

    homo_bands = []
    for i in range(dos.shape[0]):
        homo_bands.append(
            homomorphic_filter(
                dos[i],
                gamma_l=args.gamma_l,
                gamma_h=args.gamma_h,
                c=args.c,
                d0=args.d0,
            )
        )
    homo = np.stack(homo_bands, axis=0)
    homo_path = out_dir / f"{prefix}_homo.tif"
    write_tif(homo_path, homo, profile, dtype="float32", descriptions=descriptions)

    denoise_bands = []
    for i in range(homo.shape[0]):
        denoise_bands.append(
            adaptive_noise_reduction(
                homo[i],
                window=args.window,
                noise_percentile=args.noise_percentile,
            )
        )
    denoise = np.stack(denoise_bands, axis=0)
    denoise_path = out_dir / f"{prefix}_denoise.tif"
    write_tif(denoise_path, denoise, profile, dtype="float32", descriptions=descriptions)

    b_i, g_i, r_i, n_i = resolve_band_indices(
        descriptions, args.blue, args.green, args.red, args.nir
    )
    ndvi = compute_ndvi(denoise[r_i], denoise[n_i])
    ndvi_path = out_dir / f"{prefix}_ndvi.tif"
    write_tif(ndvi_path, ndvi[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI"])

    ndvi_png = out_dir / f"{prefix}_ndvi.png"
    save_png(ndvi_png, ndvi_colormap(ndvi))

    return ndvi, profile


def main():
    parser = argparse.ArgumentParser(
        description="Run DOS -> homomorphic -> denoise -> NDVI and output NDVI diff."
    )
    parser.add_argument("--image-a", required=True, help="First GeoTIFF (A)")
    parser.add_argument("--image-b", required=True, help="Second GeoTIFF (B)")
    parser.add_argument("--output", default="outputs/ndvi_diff_runs", help="Output root")
    parser.add_argument("--tag", default=None, help="Output folder name")
    parser.add_argument("--blue", default="B2", help="Blue band name")
    parser.add_argument("--green", default="B3", help="Green band name")
    parser.add_argument("--red", default="B4", help="Red band name")
    parser.add_argument("--nir", default="B8", help="NIR band name")
    parser.add_argument("--dos-percentile", type=float, default=1.0, help="DOS percentile")
    parser.add_argument("--gamma-l", type=float, default=0.5, help="Homomorphic low gain")
    parser.add_argument("--gamma-h", type=float, default=1.5, help="Homomorphic high gain")
    parser.add_argument("--c", type=float, default=1.0, help="Homomorphic sharpness")
    parser.add_argument("--d0", type=float, default=30.0, help="Homomorphic cutoff")
    parser.add_argument("--window", type=int, default=7, help="Denoise window (odd)")
    parser.add_argument(
        "--noise-percentile",
        type=float,
        default=10.0,
        help="Denoise noise percentile",
    )
    parser.add_argument("--diff-vmin", type=float, default=-0.5, help="Diff colormap min")
    parser.add_argument("--diff-vmax", type=float, default=0.5, help="Diff colormap max")
    args = parser.parse_args()

    path_a = Path(args.image_a)
    path_b = Path(args.image_b)
    if not path_a.exists() or not path_b.exists():
        raise FileNotFoundError("One or both input images do not exist.")

    tag = args.tag
    if not tag:
        tag = f"{path_a.stem}_vs_{path_b.stem}"
    out_dir = Path(args.output) / tag
    ensure_dir(out_dir)

    ndvi_a, profile = process_image(path_a, args, out_dir, "a")
    ndvi_b, _ = process_image(path_b, args, out_dir, "b")

    diff = ndvi_b.astype(np.float32) - ndvi_a.astype(np.float32)
    diff_name = f"ndvi_diff_{tag.lower()}.tif"
    diff_path = out_dir / diff_name
    write_tif(diff_path, diff[np.newaxis, :, :], profile, dtype="float32", descriptions=["NDVI_DIFF"])

    diff_png = out_dir / diff_name.replace(".tif", ".png")
    save_png(diff_png, diff_colormap(diff, vmin=args.diff_vmin, vmax=args.diff_vmax))

    print("Wrote", diff_path)
    print("Wrote", diff_png)


if __name__ == "__main__":
    main()
```

## Appendix B: MATLAB code

### matlab/Common.m

```matlab
﻿classdef Common
    methods(Static)
        function ensure_dir(path)
            if nargin < 1 || isempty(path)
                return;
            end
            if ~exist(path, 'dir')
                mkdir(path);
            end
        end

        function files = list_tifs(input_dir)
            if nargin < 1 || isempty(input_dir)
                files = {};
                return;
            end
            d = dir(fullfile(input_dir, '*.tif'));
            names = {d.name};
            [~, idx] = sort(lower(names));
            d = d(idx);
            files = fullfile({d.folder}, {d.name});
        end

        function [data, R, info] = read_tif(path)
            info = [];
            try
                info = geotiffinfo(path);
            catch
            end
            try
                [data, R] = readgeoraster(path);
            catch
                data = imread(path);
                R = [];
            end
            data = single(data);
            if ndims(data) == 2
                data = reshape(data, size(data,1), size(data,2), 1);
            end
        end

        function write_tif(path, data, R, info, descriptions)
            if nargin < 5
                descriptions = {};
            end
            Common.ensure_dir(fileparts(path));
            if nargin < 4
                info = [];
            end
            if isempty(R)
                error('No spatial referencing object for geotiffwrite.');
            end
            try
                if ~isempty(info) && isfield(info, 'GeoTIFFTags') && isfield(info.GeoTIFFTags, 'GeoKeyDirectoryTag')
                    geotiffwrite(path, data, R, 'GeoKeyDirectoryTag', info.GeoTIFFTags.GeoKeyDirectoryTag);
                else
                    geotiffwrite(path, data, R);
                end
            catch
                geotiffwrite(path, data, R);
            end
        end

        function names = band_descriptions(info, band_count)
            names = {};
            if nargin < 2
                band_count = 0;
            end
            if isempty(info)
                if band_count > 0
                    names = repmat({''}, 1, band_count);
                end
                return;
            end
            if isfield(info, 'Band') && ~isempty(info.Band)
                try
                    if isstruct(info.Band) && isfield(info.Band, 'Description')
                        descs = {info.Band.Description};
                        if ~isempty(descs)
                            names = descs;
                        end
                    end
                catch
                end
            end
            if isempty(names) && isfield(info, 'ImageDescription') && ischar(info.ImageDescription)
                txt = info.ImageDescription;
                if contains(txt, ',')
                    parts = strsplit(txt, ',');
                    names = strtrim(parts);
                end
            end
            if isempty(names) && band_count > 0
                names = repmat({''}, 1, band_count);
            end
            if band_count > 0 && numel(names) < band_count
                names = [names repmat({''}, 1, band_count - numel(names))];
            end
        end

        function mapping = band_indices_from_names(names)
            mapping = containers.Map();
            for i = 1:numel(names)
                name = names{i};
                if ~isempty(name)
                    mapping(name) = i;
                end
            end
        end

        function crs = crs_string(info)
            crs = '';
            if isempty(info)
                return;
            end
            if isfield(info, 'GeoTIFFCodes')
                if isfield(info.GeoTIFFCodes, 'PCS') && ~isempty(info.GeoTIFFCodes.PCS)
                    crs = num2str(info.GeoTIFFCodes.PCS);
                    return;
                end
                if isfield(info.GeoTIFFCodes, 'GCS') && ~isempty(info.GeoTIFFCodes.GCS)
                    crs = num2str(info.GeoTIFFCodes.GCS);
                    return;
                end
            end
        end

        function out = box_filter(img, k)
            if mod(k, 2) == 0
                error('k must be odd');
            end
            pad = floor(k / 2);
            padded = padarray(img, [pad pad], 'symmetric');
            csum = cumsum(cumsum(padded, 1), 2);
            csum = padarray(csum, [1 1], 0, 'pre');
            sum_ = csum(1+k:end, 1+k:end) - csum(1:end-k, 1+k:end) ...
                - csum(1+k:end, 1:end-k) + csum(1:end-k, 1:end-k);
            out = sum_ / (k * k);
        end

        function out = dark_object_subtraction(data, percentile)
            if nargin < 2
                percentile = 1.0;
            end
            out = zeros(size(data), 'single');
            bands = size(data, 3);
            for i = 1:bands
                band = single(data(:,:,i));
                haze = prctile(band(:), percentile);
                band = band - haze;
                band(band < 0) = 0;
                out(:,:,i) = band;
            end
        end

        function out = homomorphic_filter(band, gamma_l, gamma_h, c, d0)
            if nargin < 2, gamma_l = 0.5; end
            if nargin < 3, gamma_h = 1.5; end
            if nargin < 4, c = 1.0; end
            if nargin < 5, d0 = 30.0; end
            band = single(band);
            max_val = prctile(band(:), 99.9);
            if max_val <= 0
                out = band;
                return;
            end
            norm = band / max_val;
            log_img = log1p(norm);
            [rows, cols] = size(band);
            u = (0:rows-1) - rows / 2;
            v = (0:cols-1) - cols / 2;
            [U, V] = meshgrid(v, u);
            D2 = U.^2 + V.^2;
            H = (gamma_h - gamma_l) * (1 - exp(-c * D2 / (d0 * d0))) + gamma_l;
            fft_img = fftshift(fft2(log_img));
            filtered = H .* fft_img;
            inv_img = ifft2(ifftshift(filtered));
            out = expm1(real(inv_img));
            out = out * max_val;
            out(out < 0) = 0;
            out = single(out);
        end

        function out = adaptive_noise_reduction(band, window, noise_percentile)
            if nargin < 2, window = 7; end
            if nargin < 3, noise_percentile = 10.0; end
            band = single(band);
            mean_ = Common.box_filter(band, window);
            mean_sq = Common.box_filter(band .* band, window);
            var_ = mean_sq - mean_ .* mean_;
            var_(var_ < 0) = 0;
            noise_var = prctile(var_(:), noise_percentile);
            eps = 1e-6;
            out = band;
            mask = var_ > noise_var + eps;
            out(mask) = band(mask) - (noise_var ./ var_(mask)) .* (band(mask) - mean_(mask));
            out(~mask) = mean_(~mask);
            out(out < 0) = 0;
            out = single(out);
        end

        function ndvi = compute_ndvi(red, nir)
            red = single(red);
            nir = single(nir);
            denom = nir + red;
            ndvi = (nir - red) ./ (denom + 1e-6);
        end

        function hue = compute_hue(red, green, blue, degrees)
            if nargin < 4, degrees = true; end
            r = single(red);
            g = single(green);
            b = single(blue);
            max_val = max(max(r, g), b);
            max_val(max_val == 0) = 1;
            r = r ./ max_val;
            g = g ./ max_val;
            b = b ./ max_val;
            num = 0.5 * ((r - g) + (r - b));
            den = sqrt((r - g).^2 + (r - b) .* (g - b)) + 1e-6;
            theta = acos(max(min(num ./ den, 1), -1));
            hue = theta;
            hue(b > g) = 2 * pi - hue(b > g);
            if degrees
                hue = hue * 180 / pi;
            end
            hue = single(hue);
        end

        function write_csv(path, rows, header)
            Common.ensure_dir(fileparts(path));
            fid = fopen(path, 'w');
            if fid < 0
                error('Unable to open %s', path);
            end
            if ~isempty(header)
                fprintf(fid, '%s\n', strjoin(header, ','));
            end
            for i = 1:size(rows, 1)
                line = rows(i, :);
                for j = 1:numel(line)
                    if j > 1
                        fprintf(fid, ',');
                    end
                    fprintf(fid, '%s', line{j});
                end
                fprintf(fid, '\n');
            end
            fclose(fid);
        end

        function out = scale_to_uint8(arr, p_low, p_high)
            if nargin < 2, p_low = 2; end
            if nargin < 3, p_high = 98; end
            arr = single(arr);
            mask = isfinite(arr);
            if ~any(mask(:))
                out = zeros(size(arr), 'uint8');
                return;
            end
            vals = arr(mask);
            vmin = prctile(vals, p_low);
            vmax = prctile(vals, p_high);
            if vmax <= vmin
                vmax = vmin + 1.0;
            end
            out = (arr - vmin) ./ (vmax - vmin);
            out = max(min(out, 1), 0);
            out = uint8(out * 255);
        end

        function rgb = ndvi_colormap(ndvi)
            x = max(min((ndvi + 1.0) / 2.0, 1), 0);
            r = ones(size(x), 'single');
            r(x >= 0.5) = 1.0 - (x(x >= 0.5) - 0.5) * 2.0;
            g = zeros(size(x), 'single');
            g(x < 0.5) = x(x < 0.5) * 2.0;
            g(x >= 0.5) = 1.0;
            b = zeros(size(x), 'single');
            rgb = uint8(cat(3, r, g, b) * 255);
        end

        function rgb = diff_colormap(diff, vmin, vmax)
            if nargin < 2, vmin = -0.5; end
            if nargin < 3, vmax = 0.5; end
            x = (diff - vmin) ./ (vmax - vmin);
            x = max(min(x, 1), 0);
            r = zeros(size(x), 'single');
            b = zeros(size(x), 'single');
            g = ones(size(x), 'single');
            r(x > 0.5) = (x(x > 0.5) - 0.5) * 2.0;
            b(x < 0.5) = (0.5 - x(x < 0.5)) * 2.0;
            g = 1.0 - (abs(x - 0.5) * 2.0);
            rgb = uint8(cat(3, r, g, b) * 255);
        end
    end
end
```

### matlab/step01_data_check.m

```matlab
﻿function step01_data_check(varargin)
    p = inputParser;
    addParameter(p, 'input', 'photos');
    addParameter(p, 'out', 'outputs/00_data_check.csv');
    parse(p, varargin{:});
    args = p.Results;

    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    rows = cell(numel(files), 7);
    for i = 1:numel(files)
        path = files{i};
        [data, ~, info] = Common.read_tif(path);
        [h, w, b] = size(data);
        names = Common.band_descriptions(info, b);
        name_str = strjoin(names, ',');
        dtype = class(data);
        dtype_str = strjoin(repmat({dtype}, 1, b), ',');
        [~, fname, ext] = fileparts(path);
        file = [fname ext];
        rows(i, :) = {file, num2str(w), num2str(h), num2str(b), Common.crs_string(info), dtype_str, name_str};
        disp([file, ': ', num2str(w), 'x', num2str(h), ', bands=', num2str(b), ', dtype=', dtype]);
    end

    Common.write_csv(args.out, rows, {'file', 'width', 'height', 'bands', 'crs', 'dtypes', 'band_names'});
    disp(['Wrote ', args.out]);
end
```

### matlab/step02_dark_object_subtraction.m

```matlab
﻿function step02_dark_object_subtraction(varargin)
    p = inputParser;
    addParameter(p, 'input', 'photos');
    addParameter(p, 'output', 'outputs/01_dos');
    addParameter(p, 'percentile', 1.0);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        out = Common.dark_object_subtraction(data, args.percentile);
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_dos.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end
```

### matlab/step03_homomorphic_filter.m

```matlab
﻿function step03_homomorphic_filter(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/01_dos');
    addParameter(p, 'output', 'outputs/02_homomorphic');
    addParameter(p, 'gamma_l', 0.5);
    addParameter(p, 'gamma_h', 1.5);
    addParameter(p, 'c', 1.0);
    addParameter(p, 'd0', 30.0);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        bands = size(data, 3);
        out = zeros(size(data), 'single');
        for b = 1:bands
            out(:,:,b) = Common.homomorphic_filter(data(:,:,b), args.gamma_l, args.gamma_h, args.c, args.d0);
        end
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_homo.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end
```

### matlab/step04_adaptive_noise_reduction.m

```matlab
﻿function step04_adaptive_noise_reduction(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/02_homomorphic');
    addParameter(p, 'output', 'outputs/03_denoised');
    addParameter(p, 'window', 7);
    addParameter(p, 'noise_percentile', 10.0);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        bands = size(data, 3);
        out = zeros(size(data), 'single');
        for b = 1:bands
            out(:,:,b) = Common.adaptive_noise_reduction(data(:,:,b), args.window, args.noise_percentile);
        end
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_denoise.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end
```

### matlab/step05_features.m

```matlab
﻿function step05_features(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/03_denoised');
    addParameter(p, 'output', 'outputs/04_features');
    addParameter(p, 'blue', 'B2');
    addParameter(p, 'green', 'B3');
    addParameter(p, 'red', 'B4');
    addParameter(p, 'nir', 'B8');
    addParameter(p, 'hue_rad', false);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        bcount = size(data, 3);
        names = Common.band_descriptions(info, bcount);
        mapping = Common.band_indices_from_names(names);
        b_i = pick_index(mapping, args.blue, 1);
        g_i = pick_index(mapping, args.green, 2);
        r_i = pick_index(mapping, args.red, 3);
        n_i = pick_index(mapping, args.nir, 4);

        blue = data(:,:,b_i);
        green = data(:,:,g_i);
        red = data(:,:,r_i);
        nir = data(:,:,n_i);

        ndvi = Common.compute_ndvi(red, nir);
        hue = Common.compute_hue(red, green, blue, ~args.hue_rad);
        out = cat(3, ndvi, hue);
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_features.tif']);
        Common.write_tif(out_path, out, R, info, {'NDVI', 'HUE'});
        disp(['Wrote ', out_path]);
    end
end

function idx = pick_index(mapping, name, fallback)
    if isKey(mapping, name)
        idx = mapping(name);
    else
        idx = fallback;
    end
end
```

### matlab/step06_kmeans_segmentation.m

```matlab
﻿function step06_kmeans_segmentation(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/04_features');
    addParameter(p, 'output', 'outputs/05_segments');
    addParameter(p, 'k', 3);
    addParameter(p, 'iterations', 10);
    addParameter(p, 'sample', 200000);
    addParameter(p, 'seed', 0);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    rng(args.seed);

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        ndvi = single(data(:,:,1));
        hue = single(data(:,:,2));
        flat = [ndvi(:), hue(:)];
        mask = all(isfinite(flat), 2);
        flat = flat(mask, :);

        if size(flat, 1) > args.sample
            idx = randperm(size(flat, 1), args.sample);
            sample = flat(idx, :);
        else
            sample = flat;
        end

        mean_ = mean(sample, 1);
        std_ = std(sample, 0, 1);
        std_(std_ == 0) = 1;
        sample_n = (sample - mean_) ./ std_;

        centers = kmeans_custom(sample_n, args.k, args.iterations, args.seed);
        centers = centers .* std_ + mean_;

        flat_n = (flat - mean_) ./ std_;
        labels = assign_labels(flat_n, centers);
        labels = uint8(labels + 1);

        full_labels = zeros(numel(ndvi), 1, 'uint8');
        full_labels(mask) = labels;
        label_img = reshape(full_labels, size(ndvi));
        out = reshape(label_img, size(ndvi,1), size(ndvi,2), 1);

        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_segments.tif']);
        Common.write_tif(out_path, out, R, info, {'SEGMENTS'});
        disp(['Wrote ', out_path]);
    end
end

function centers = kmeans_custom(features, k, iterations, seed)
    rng(seed);
    centers = initialize_centers(features, k, seed);
    for iter = 1:iterations
        labels = assign_labels(features, centers);
        for i = 1:k
            mask = labels == (i - 1);
            if any(mask)
                centers(i, :) = mean(features(mask, :), 1);
            end
        end
    end
end

function centers = initialize_centers(features, k, seed)
    rng(seed);
    ndvi = features(:,1);
    hue = features(:,2);
    p = prctile(ndvi, [10 50 90]);
    h50 = prctile(hue, 50);
    centers = [p(1) h50; p(2) h50; p(3) h50];
    if k ~= 3
        idx = randperm(size(features,1), k);
        centers = features(idx, :);
    end
end

function labels = assign_labels(features, centers)
    dists = zeros(size(features,1), size(centers,1));
    for i = 1:size(centers,1)
        diff = features - centers(i, :);
        dists(:, i) = sum(diff.^2, 2);
    end
    [~, labels] = min(dists, [], 2);
    labels = labels - 1;
end
```

### matlab/step07_temporal_analysis.m

```matlab
﻿function step07_temporal_analysis(varargin)
    p = inputParser;
    addParameter(p, 'features', 'outputs/04_features');
    addParameter(p, 'features_2016', '');
    addParameter(p, 'features_2024', '');
    addParameter(p, 'bands', 'outputs/03_denoised');
    addParameter(p, 'output', 'outputs/06_temporal');
    addParameter(p, 'ndvi_threshold', 0.3);
    addParameter(p, 'ndvi_max', []);
    addParameter(p, 'green_red_ratio', 1.05);
    addParameter(p, 'nir_red_ratio', 1.2);
    addParameter(p, 'ndwi_threshold', 0.0);
    addParameter(p, 'land_intersection', false);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    feat_files = Common.list_tifs(args.features);
    if isempty(feat_files) && isempty(args.features_2016) && isempty(args.features_2024)
        disp('Missing feature files.');
        return;
    end

    feat_map = containers.Map();
    for i = 1:numel(feat_files)
        [city, year] = parse_city_year(feat_files{i});
        if ~isempty(city)
            key = make_key(city, year);
            feat_map(key) = feat_files{i};
        end
    end

    if ~isempty(args.features_2016)
        extra = Common.list_tifs(args.features_2016);
        for i = 1:numel(extra)
            [city, year] = parse_city_year(extra{i});
            if ~isempty(city) && year == 2016
                feat_map(make_key(city, year)) = extra{i};
            end
        end
    end

    if ~isempty(args.features_2024)
        extra = Common.list_tifs(args.features_2024);
        for i = 1:numel(extra)
            [city, year] = parse_city_year(extra{i});
            if ~isempty(city) && year == 2024
                feat_map(make_key(city, year)) = extra{i};
            end
        end
    end

    keys = feat_map.keys;
    rows = {};

    for i = 1:numel(keys)
        key = keys{i};
        parts = strsplit(key, '|');
        city = parts{1};
        year = str2double(parts{2});
        other_year = 2024;
        if year == 2024
            other_year = 2016;
        end
        other_key = make_key(city, other_year);
        if ~isKey(feat_map, other_key)
            continue;
        end

        feat_path = feat_map(key);
        other_path = feat_map(other_key);

        [feat1, R, info] = Common.read_tif(feat_path);
        [feat2, ~, ~] = Common.read_tif(other_path);

        ndvi1 = feat1(:,:,1);
        ndvi2 = feat2(:,:,1);

        base1 = strip_suffix(feat_path);
        base2 = strip_suffix(other_path);
        base1 = strrep(base1, '_features', '');
        base2 = strrep(base2, '_features', '');
        bands1 = fullfile(args.bands, [base1 '.tif']);
        bands2 = fullfile(args.bands, [base2 '.tif']);

        if exist(bands1, 'file') && exist(bands2, 'file')
            [b1, g1, r1, n1] = load_bands(bands1);
            [b2, g2, r2, n2] = load_bands(bands2);
            ndwi1 = compute_ndwi(g1, n1);
            ndwi2 = compute_ndwi(g2, n2);
            water1 = ndwi1 > args.ndwi_threshold;
            water2 = ndwi2 > args.ndwi_threshold;
        else
            water1 = false(size(ndvi1));
            water2 = false(size(ndvi2));
            b1 = []; g1 = []; r1 = []; n1 = [];
            b2 = []; g2 = []; r2 = []; n2 = [];
        end

        land1 = ~water1;
        land2 = ~water2;
        if args.land_intersection
            land1 = land1 & land2;
            land2 = land1;
        end

        veg1 = (ndvi1 > args.ndvi_threshold) & land1;
        veg2 = (ndvi2 > args.ndvi_threshold) & land2;
        if ~isempty(args.ndvi_max)
            veg1 = veg1 & (ndvi1 <= args.ndvi_max);
            veg2 = veg2 & (ndvi2 <= args.ndvi_max);
        end
        if ~isempty(r1)
            gr1 = g1 ./ (r1 + 1e-6);
            nr1 = n1 ./ (r1 + 1e-6);
            veg1 = veg1 & (gr1 > args.green_red_ratio) & (nr1 > args.nir_red_ratio);
        end
        if ~isempty(r2)
            gr2 = g2 ./ (r2 + 1e-6);
            nr2 = n2 ./ (r2 + 1e-6);
            veg2 = veg2 & (gr2 > args.green_red_ratio) & (nr2 > args.nir_red_ratio);
        end

        total1 = sum(land1(:));
        total2 = sum(land2(:));
        pct1 = double(sum(veg1(:))) / max(total1, 1) * 100.0;
        pct2 = double(sum(veg2(:))) / max(total2, 1) * 100.0;
        delta = pct2 - pct1;

        rows(end+1, :) = {city, num2str(year), num2str(other_year), sprintf('%.2f', pct1), sprintf('%.2f', pct2), sprintf('%.2f', delta)}; %#ok<AGROW>

        diff = zeros(size(veg1), 'int8');
        diff(veg1 & ~veg2) = -1;
        diff(~veg1 & veg2) = 1;
        diff(water1 & water2) = 0;

        diff_path = fullfile(args.output, [city '_' num2str(year) '_' num2str(other_year) '_veg_diff.tif']);
        out = reshape(diff, size(diff,1), size(diff,2), 1);
        Common.write_tif(diff_path, out, R, info, {'VEG_DIFF'});
        disp(['Wrote ', diff_path]);
    end

    out_csv = fullfile(args.output, 'summary.csv');
    Common.write_csv(out_csv, rows, {'city', 'year_a', 'year_b', 'veg_pct_a', 'veg_pct_b', 'delta_pct'});
    disp(['Wrote ', out_csv]);
end

function [city, year] = parse_city_year(path)
    [~, name] = fileparts(path);
    tokens = regexp(name, '^(?<city>.+)_(?<year>\d{4})_', 'names');
    if isempty(tokens)
        city = '';
        year = [];
        return;
    end
    city = tokens.city;
    year = str2double(tokens.year);
end

function key = make_key(city, year)
    key = [city '|' num2str(year)];
end

function base = strip_suffix(path)
    [~, base] = fileparts(path);
end

function ndwi = compute_ndwi(green, nir)
    green = single(green);
    nir = single(nir);
    denom = green + nir;
    ndwi = (green - nir) ./ (denom + 1e-6);
end

function [blue, green, red, nir] = load_bands(path)
    [data, ~, info] = Common.read_tif(path);
    bcount = size(data, 3);
    names = Common.band_descriptions(info, bcount);
    mapping = Common.band_indices_from_names(names);
    b_i = pick_index(mapping, 'B2', 1);
    g_i = pick_index(mapping, 'B3', 2);
    r_i = pick_index(mapping, 'B4', 3);
    n_i = pick_index(mapping, 'B8', 4);
    blue = data(:,:,b_i);
    green = data(:,:,g_i);
    red = data(:,:,r_i);
    nir = data(:,:,n_i);
end

function idx = pick_index(mapping, name, fallback)
    if isKey(mapping, name)
        idx = mapping(name);
    else
        idx = fallback;
    end
end
```

### matlab/step08_export_pngs.m

```matlab
﻿function step08_export_pngs(varargin)
    p = inputParser;
    addParameter(p, 'root', '.');
    addParameter(p, 'output', 'outputs/png');
    parse(p, varargin{:});
    args = p.Results;

    root = fullfile(pwd, args.root);
    out_root = fullfile(root, args.output);

    tif_paths = [list_tifs_recursive(fullfile(root, 'photos')); list_tifs_recursive(fullfile(root, 'outputs'))];
    if isempty(tif_paths)
        disp('No .tif files found.');
        return;
    end

    for i = 1:numel(tif_paths)
        tif_path = tif_paths{i};
        rel = strrep(fileparts(tif_path), root, '');
        if startsWith(rel, filesep)
            rel = rel(2:end);
        end
        out_dir = fullfile(out_root, rel);
        export_tif(tif_path, out_dir);
        disp(['Exported ', tif_path, ' -> ', out_dir]);
    end
end

function export_tif(tif_path, out_dir)
    [data, ~, info] = Common.read_tif(tif_path);
    names = Common.band_descriptions(info, size(data, 3));
    mapping = Common.band_indices_from_names(names);

    Common.ensure_dir(out_dir);
    [~, stem] = fileparts(tif_path);
    count = size(data, 3);

    if count >= 3 && isKey(mapping, 'B2') && isKey(mapping, 'B3') && isKey(mapping, 'B4')
        b = Common.scale_to_uint8(data(:,:,mapping('B2')));
        g = Common.scale_to_uint8(data(:,:,mapping('B3')));
        r = Common.scale_to_uint8(data(:,:,mapping('B4')));
        rgb = cat(3, r, g, b);
        imwrite(rgb, fullfile(out_dir, [stem '_rgb.png']));
    elseif count >= 3
        r = Common.scale_to_uint8(data(:,:,1));
        g = Common.scale_to_uint8(data(:,:,2));
        b = Common.scale_to_uint8(data(:,:,3));
        rgb = cat(3, r, g, b);
        imwrite(rgb, fullfile(out_dir, [stem '_rgb.png']));
    end

    if count == 1
        band = Common.scale_to_uint8(data(:,:,1));
        imwrite(band, fullfile(out_dir, [stem '.png']));
    elseif count == 2
        name1 = safe_name(names, 1, 'band1');
        name2 = safe_name(names, 2, 'band2');
        imwrite(Common.scale_to_uint8(data(:,:,1)), fullfile(out_dir, [stem '_' lower(name1) '.png']));
        imwrite(Common.scale_to_uint8(data(:,:,2)), fullfile(out_dir, [stem '_' lower(name2) '.png']));
    elseif count > 3
        for i = 1:count
            name = safe_name(names, i, ['band' num2str(i)]);
            imwrite(Common.scale_to_uint8(data(:,:,i)), fullfile(out_dir, [stem '_' lower(name) '.png']));
        end
    end
end

function name = safe_name(names, idx, fallback)
    if idx <= numel(names) && ~isempty(names{idx})
        name = names{idx};
    else
        name = fallback;
    end
end

function files = list_tifs_recursive(root_dir)
    if ~exist(root_dir, 'dir')
        files = {};
        return;
    end
    d = dir(fullfile(root_dir, '**', '*.tif'));
    files = fullfile({d.folder}, {d.name});
end
```

### matlab/step09_ndvi_colormap_diff.m

```matlab
﻿function step09_ndvi_colormap_diff(varargin)
    p = inputParser;
    addParameter(p, 'features', 'outputs/04_features');
    addParameter(p, 'out_ndvi', 'outputs/07_ndvi_png');
    addParameter(p, 'out_diff', 'outputs/08_ndvi_diff');
    parse(p, varargin{:});
    args = p.Results;

    features = Common.list_tifs(args.features);
    if isempty(features)
        disp('No feature .tif files found.');
        return;
    end

    Common.ensure_dir(args.out_ndvi);
    Common.ensure_dir(args.out_diff);

    by_city_year = containers.Map();
    for i = 1:numel(features)
        path = features{i};
        [city, year] = parse_city_year(path);
        if ~isempty(city)
            by_city_year(make_key(city, year)) = path;
        end
    end

    stats = {};
    keys = by_city_year.keys;
    for i = 1:numel(keys)
        key = keys{i};
        parts = strsplit(key, '|');
        city = parts{1};
        year = str2double(parts{2});
        feat_path = by_city_year(key);
        [data, ~, ~] = Common.read_tif(feat_path);
        ndvi = single(data(:,:,1));
        rgb = Common.ndvi_colormap(ndvi);
        out_path = fullfile(args.out_ndvi, [city '_' num2str(year) '_ndvi.png']);
        imwrite(rgb, out_path);
        stats(end+1, :) = {city, num2str(year), sprintf('%.4f', mean(ndvi(~isnan(ndvi)), 'all'))}; %#ok<AGROW>
    end

    for i = 1:numel(keys)
        parts = strsplit(keys{i}, '|');
        city = parts{1};
        if isKey(by_city_year, make_key(city, 2016)) && isKey(by_city_year, make_key(city, 2024))
            [ndvi16, R, info] = Common.read_tif(by_city_year(make_key(city, 2016)));
            [ndvi24, ~, ~] = Common.read_tif(by_city_year(make_key(city, 2024)));
            diff = single(ndvi24(:,:,1)) - single(ndvi16(:,:,1));
            diff_tif = fullfile(args.out_diff, [city '_ndvi_diff_2024_2016.tif']);
            out = reshape(diff, size(diff,1), size(diff,2), 1);
            Common.write_tif(diff_tif, out, R, info, {'NDVI_DIFF'});
            diff_png = fullfile(args.out_diff, [city '_ndvi_diff_2024_2016.png']);
            imwrite(Common.diff_colormap(diff), diff_png);
            stats(end+1, :) = {city, '2024-2016', sprintf('%.4f', mean(diff(~isnan(diff)), 'all'))}; %#ok<AGROW>
        end
    end

    Common.write_csv(fullfile(args.out_diff, 'ndvi_stats.csv'), stats, {'city', 'year_or_diff', 'mean_ndvi'});
    disp(['Wrote NDVI PNGs to ', args.out_ndvi]);
    disp(['Wrote NDVI diffs to ', args.out_diff]);
end

function [city, year] = parse_city_year(path)
    [~, name] = fileparts(path);
    tokens = regexp(name, '^(?<city>.+)_(?<year>\d{4})_', 'names');
    if isempty(tokens)
        city = '';
        year = [];
        return;
    end
    city = tokens.city;
    year = str2double(tokens.year);
end

function key = make_key(city, year)
    key = [city '|' num2str(year)];
end
```

### matlab/step10_color_istanbul_diff.m

```matlab
﻿function step10_color_istanbul_diff(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/06_temporal/Istanbul_2016_2024_veg_diff.tif');
    addParameter(p, 'output', 'outputs/06_temporal/Istanbul_veg_change_red_yellow.png');
    parse(p, varargin{:});
    args = p.Results;

    if ~exist(args.input, 'file')
        error(['Missing diff file: ', args.input]);
    end

    [diff, ~, ~] = Common.read_tif(args.input);
    diff = diff(:,:,1);

    [h, w] = size(diff);
    rgb = zeros(h, w, 3, 'uint8');
    loss = diff == -1;
    gain = diff == 1;

    rgb(:,:,1) = uint8(loss) * 255;
    rgb(:,:,1) = rgb(:,:,1) + uint8(gain) * 255;
    rgb(:,:,2) = uint8(gain) * 255;

    Common.ensure_dir(fileparts(args.output));
    imwrite(rgb, args.output);
    disp(['Wrote ', args.output]);
end
```

### matlab/step11_radiometric_normalization.m

```matlab
﻿function step11_radiometric_normalization(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/01_dos');
    addParameter(p, 'output', 'outputs/01_dos_norm');
    addParameter(p, 'quantiles', 1024);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    by_city_year = containers.Map();
    for i = 1:numel(files)
        [city, year] = parse_city_year(files{i});
        if ~isempty(city)
            by_city_year(make_key(city, year)) = files{i};
        end
    end

    keys = by_city_year.keys;
    for i = 1:numel(keys)
        parts = strsplit(keys{i}, '|');
        city = parts{1};
        year = str2double(parts{2});
        if year ~= 2024
            continue;
        end
        ref_key = make_key(city, 2016);
        if ~isKey(by_city_year, ref_key)
            continue;
        end

        src_path = by_city_year(keys{i});
        ref_path = by_city_year(ref_key);
        [src_data, R, info] = Common.read_tif(src_path);
        [ref_data, ~, ~] = Common.read_tif(ref_path);

        out = zeros(size(src_data), 'single');
        for b = 1:size(src_data, 3)
            out(:,:,b) = match_histogram_quantiles(src_data(:,:,b), ref_data(:,:,b), args.quantiles);
        end

        [~, name] = fileparts(src_path);
        out_path = fullfile(args.output, [name '_norm.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end

function [city, year] = parse_city_year(path)
    [~, name] = fileparts(path);
    tokens = regexp(name, '^(?<city>.+)_(?<year>\d{4})_', 'names');
    if isempty(tokens)
        city = '';
        year = [];
        return;
    end
    city = tokens.city;
    year = str2double(tokens.year);
end

function key = make_key(city, year)
    key = [city '|' num2str(year)];
end

function matched = match_histogram_quantiles(source, reference, quantiles)
    src = single(source);
    ref = single(reference);
    mask_src = isfinite(src);
    mask_ref = isfinite(ref);
    if ~any(mask_src(:)) || ~any(mask_ref(:))
        matched = src;
        return;
    end
    qs = linspace(0.0, 1.0, quantiles);
    src_q = quantile(src(mask_src), qs);
    ref_q = quantile(ref(mask_ref), qs);
    src_q = max_accumulate(src_q);
    ref_q = max_accumulate(ref_q);
    flat = src(:);
    matched = interp1(src_q, ref_q, flat, 'linear', 'extrap');
    matched = reshape(matched, size(src));
    matched = single(matched);
end

function out = max_accumulate(x)
    out = x;
    for i = 2:numel(out)
        if out(i) < out(i-1)
            out(i) = out(i-1);
        end
    end
end
```

### matlab/step12_radiometric_normalization_pair.m

```matlab
﻿function step12_radiometric_normalization_pair(varargin)
    p = inputParser;
    addParameter(p, 'ref_2016', '');
    addParameter(p, 'ref_2024', '');
    addParameter(p, 'output', 'outputs/01_dos_norm_pair');
    addParameter(p, 'quantiles', 1024);
    parse(p, varargin{:});
    args = p.Results;

    if isempty(args.ref_2016) || isempty(args.ref_2024)
        error('ref_2016 and ref_2024 are required.');
    end

    Common.ensure_dir(args.output);
    [d16, R, info] = Common.read_tif(args.ref_2016);
    [d24, ~, ~] = Common.read_tif(args.ref_2024);

    out16 = zeros(size(d16), 'single');
    out24 = zeros(size(d24), 'single');

    for b = 1:size(d16, 3)
        band16 = d16(:,:,b);
        band24 = d24(:,:,b);
        ref_q = (single(band16) + single(band24)) / 2.0;
        out16(:,:,b) = match_histogram_quantiles(band16, ref_q, args.quantiles);
        out24(:,:,b) = match_histogram_quantiles(band24, ref_q, args.quantiles);
    end

    [~, name16] = fileparts(args.ref_2016);
    [~, name24] = fileparts(args.ref_2024);
    out16_path = fullfile(args.output, [name16 '_normpair.tif']);
    out24_path = fullfile(args.output, [name24 '_normpair.tif']);
    Common.write_tif(out16_path, out16, R, info, {});
    Common.write_tif(out24_path, out24, R, info, {});
    disp(['Wrote ', out16_path]);
    disp(['Wrote ', out24_path]);
end

function matched = match_histogram_quantiles(source, reference, quantiles)
    src = single(source);
    ref = single(reference);
    mask_src = isfinite(src);
    mask_ref = isfinite(ref);
    if ~any(mask_src(:)) || ~any(mask_ref(:))
        matched = src;
        return;
    end
    qs = linspace(0.0, 1.0, quantiles);
    src_q = quantile(src(mask_src), qs);
    ref_q = quantile(ref(mask_ref), qs);
    src_q = max_accumulate(src_q);
    ref_q = max_accumulate(ref_q);
    flat = src(:);
    matched = interp1(src_q, ref_q, flat, 'linear', 'extrap');
    matched = reshape(matched, size(src));
    matched = single(matched);
end

function out = max_accumulate(x)
    out = x;
    for i = 2:numel(out)
        if out(i) < out(i-1)
            out(i) = out(i-1);
        end
    end
end
```

### matlab/run_ndvi_diff_pipeline.m

```matlab
﻿function run_ndvi_diff_pipeline(varargin)
    p = inputParser;
    addParameter(p, 'image_a', '');
    addParameter(p, 'image_b', '');
    addParameter(p, 'output', 'outputs/ndvi_diff_runs');
    addParameter(p, 'tag', '');
    addParameter(p, 'blue', 'B2');
    addParameter(p, 'green', 'B3');
    addParameter(p, 'red', 'B4');
    addParameter(p, 'nir', 'B8');
    addParameter(p, 'dos_percentile', 1.0);
    addParameter(p, 'gamma_l', 0.5);
    addParameter(p, 'gamma_h', 1.5);
    addParameter(p, 'c', 1.0);
    addParameter(p, 'd0', 30.0);
    addParameter(p, 'window', 7);
    addParameter(p, 'noise_percentile', 10.0);
    addParameter(p, 'diff_vmin', -0.5);
    addParameter(p, 'diff_vmax', 0.5);
    parse(p, varargin{:});
    args = p.Results;

    if isempty(args.image_a) || isempty(args.image_b)
        error('image_a and image_b are required.');
    end
    if ~exist(args.image_a, 'file') || ~exist(args.image_b, 'file')
        error('One or both input images do not exist.');
    end

    if isempty(args.tag)
        [~, a_name] = fileparts(args.image_a);
        [~, b_name] = fileparts(args.image_b);
        args.tag = [a_name '_vs_' b_name];
    end

    out_dir = fullfile(args.output, args.tag);
    Common.ensure_dir(out_dir);

    [ndvi_a, R, info] = process_image(args.image_a, args, out_dir, 'a');
    [ndvi_b, ~, ~] = process_image(args.image_b, args, out_dir, 'b');

    diff = single(ndvi_b) - single(ndvi_a);
    diff_name = ['ndvi_diff_' lower(args.tag)];
    diff_path = fullfile(out_dir, [diff_name '.tif']);
    out = reshape(diff, size(diff,1), size(diff,2), 1);
    Common.write_tif(diff_path, out, R, info, {'NDVI_DIFF'});

    diff_png = fullfile(out_dir, [diff_name '.png']);
    imwrite(Common.diff_colormap(diff, args.diff_vmin, args.diff_vmax), diff_png);

    disp(['Wrote ', diff_path]);
    disp(['Wrote ', diff_png]);
end

function [ndvi, R, info] = process_image(path, args, out_dir, prefix)
    [data, R, info] = Common.read_tif(path);

    dos = Common.dark_object_subtraction(data, args.dos_percentile);
    dos_path = fullfile(out_dir, [prefix '_dos.tif']);
    Common.write_tif(dos_path, dos, R, info, {});

    bands = size(dos, 3);
    homo = zeros(size(dos), 'single');
    for b = 1:bands
        homo(:,:,b) = Common.homomorphic_filter(dos(:,:,b), args.gamma_l, args.gamma_h, args.c, args.d0);
    end
    homo_path = fullfile(out_dir, [prefix '_homo.tif']);
    Common.write_tif(homo_path, homo, R, info, {});

    denoise = zeros(size(homo), 'single');
    for b = 1:bands
        denoise(:,:,b) = Common.adaptive_noise_reduction(homo(:,:,b), args.window, args.noise_percentile);
    end
    denoise_path = fullfile(out_dir, [prefix '_denoise.tif']);
    Common.write_tif(denoise_path, denoise, R, info, {});

    names = Common.band_descriptions(info, bands);
    mapping = Common.band_indices_from_names(names);
    b_i = pick_index(mapping, args.blue, 1);
    g_i = pick_index(mapping, args.green, 2);
    r_i = pick_index(mapping, args.red, 3);
    n_i = pick_index(mapping, args.nir, 4);

    ndvi = Common.compute_ndvi(denoise(:,:,r_i), denoise(:,:,n_i));
    ndvi_path = fullfile(out_dir, [prefix '_ndvi.tif']);
    Common.write_tif(ndvi_path, reshape(ndvi, size(ndvi,1), size(ndvi,2), 1), R, info, {'NDVI'});

    ndvi_png = fullfile(out_dir, [prefix '_ndvi.png']);
    imwrite(Common.ndvi_colormap(ndvi), ndvi_png);
end

function idx = pick_index(mapping, name, fallback)
    if isKey(mapping, name)
        idx = mapping(name);
    else
        idx = fallback;
    end
end
```