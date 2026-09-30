# Project Run Guide (Method 1)

This guide explains how to reproduce the Istanbul pipeline and how to change inputs.

## Requirements

- Python 3.9+
- Packages: `rasterio`, `numpy`, `Pillow`

Install:
```
pip install rasterio numpy pillow
```

## Inputs

Place GeoTIFFs in `photos/` with band names that include:
- B2 (Blue), B3 (Green), B4 (Red), B8 (NIR)

Files used for Istanbul:
- `photos/Istanbul_2016_TOA.tif`
- `photos/Istanbul_2024_TOA.tif`

## One-Command Run

Run the full Method 1 pipeline:
```
./run_method1.ps1
```

## Step-by-Step Run

1) Dark Object Subtraction (DOS)
```
python scripts/02_dark_object_subtraction.py --input photos --output outputs/istanbul_dos
```

2) Homomorphic Filtering
```
python scripts/03_homomorphic_filter.py --input outputs/istanbul_dos --output outputs/istanbul_homo
```

3) Adaptive Noise Reduction
```
python scripts/04_adaptive_noise_reduction.py --input outputs/istanbul_homo --output outputs/istanbul_denoise
```

4) Feature Extraction (NDVI + Hue)
```
python scripts/05_features.py --input outputs/istanbul_denoise --output outputs/istanbul_features_m1
```

5) NDVI Maps + Diff Maps
```
python scripts/09_ndvi_colormap_diff.py --features outputs/istanbul_features_m1 --out-ndvi outputs/istanbul_png_m1 --out-diff outputs/istanbul_ndvi_diff_m1
```

6) Vegetation Change Summary (Method 1)
```
python scripts/07_temporal_analysis.py --features-2016 outputs/istanbul_features_m1 --features-2024 outputs/istanbul_features_m1 --bands outputs/istanbul_denoise --output outputs/istanbul_results_m1_t07 --ndvi-threshold 0.7 --ndwi-threshold 0.0 --land-intersection --green-red-ratio 1.05 --nir-red-ratio 1.2
```

Outputs:
- NDVI PNGs: `outputs/istanbul_png_m1`
- NDVI diff maps: `outputs/istanbul_ndvi_diff_m1`
- Vegetation summary: `outputs/istanbul_results_m1_t07/summary.csv`

## Changing Inputs / Cities

1) Place new `.tif` files in `photos/`.
2) Re-run the pipeline. For a different city, adjust file names or move only the city files into `photos/` before running.

## Notes

- NDVI requires NIR band (B8). Files without NIR cannot produce NDVI.
- The NDVI threshold used here is 0.7 (best visual match to RGB for Istanbul).
