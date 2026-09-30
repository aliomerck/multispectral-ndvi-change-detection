# Pipeline Summary (Standalone Script)

This document explains the steps and outputs from `scripts/15_full_pipeline_standalone.py`.
It uses only raw GeoTIFFs and does not depend on `common.py`.

## What the script does
Inputs (default):
- `photos/Istanbul_2016_TOA.tif`
- `photos/Istanbul_2024_TOA.tif`

Processing steps:
1) **Dark Object Subtraction (DOS)**  
   We assume very dark pixels should be near zero. The haze level is estimated from a low
   percentile and subtracted from every band:
   `band = max(band - percentile(band), 0)`

2) **Homomorphic filtering**  
   We model the image as `f(x,y) = i(x,y) * r(x,y)` and take log to separate illumination and
   reflectance. A high‑boost filter in the frequency domain reduces low‑frequency illumination
   and enhances reflectance before we transform back.

3) **Adaptive local noise reduction**  
   A local variance filter keeps edges and smooths flat regions:
   `f_hat = g - (sigma_n^2 / sigma_L^2) * (g - m_L)`

4) **NDVI**  
   `NDVI = (NIR - Red) / (NIR + Red + eps)`  
   We save NDVI maps for 2016 and 2024.

5) **NDVI difference map**  
   `NDVI_2024 - NDVI_2016` is saved as TIF + PNG.

6) **Thresholded NDVI loss (0.7)**  
   Vegetation is `NDVI >= 0.7`. Loss is pixels that were vegetation in 2016 but not in 2024.

7) **K‑means on RGB + green loss**  
   We equalize each RGB band to make colors more separable, run k‑means clustering,
   then pick the “greenish” cluster by the highest mean green ratio:
   `G / (R + G + B)`  
   The green loss map is green(2016) AND NOT green(2024).

## Outputs
All outputs are written to `outputs/standalone_run/` by default.

Key files:
- `2016_dos.tif`, `2016_homo.tif`, `2016_denoise.tif`, `2016_ndvi.tif`, `2016_ndvi.png`
- `2024_dos.tif`, `2024_homo.tif`, `2024_denoise.tif`, `2024_ndvi.tif`, `2024_ndvi.png`
- `ndvi_diff_2024_2016.tif`, `ndvi_diff_2024_2016.png`
- `ndvi_loss_thresh_0.7.tif`, `ndvi_loss_thresh_0.7.png`
- `2016_rgb_kmeans.tif`, `2016_rgb_kmeans.png`
- `2024_rgb_kmeans.tif`, `2024_rgb_kmeans.png`
- `2016_green_mask.tif`, `2016_green_mask.png`
- `2024_green_mask.tif`, `2024_green_mask.png`
- `green_loss_2016_2024.tif`, `green_loss_2016_2024.png`
- `summary.txt` (green % for 2016/2024 + loss %)

## How to run

```powershell
python scripts\15_full_pipeline_standalone.py
```

Optional example with custom paths:

```powershell
python scripts\15_full_pipeline_standalone.py ^
  --image-2016 photos\Istanbul_2016_TOA.tif ^
  --image-2024 photos\Istanbul_2024_TOA.tif ^
  --output outputs\standalone_run
```
