# Multispectral NDVI Change Detection

Term project for EE475 (Digital Image Processing).

This repository contains a Python pipeline for radiometric correction, denoising, feature extraction, and NDVI change analysis on multispectral GeoTIFFs.
It was developed as a two-person course project and applied to Istanbul imagery from 2016 and 2024.

## Results

Study area: Istanbul, multispectral GeoTIFFs from 2016 and 2024 (bands B2/B3/B4/B8, roughly 4000 x 3000 px, no SWIR band available).

![NDVI 2016, NDVI 2024 and the difference map](docs/results/overview_ndvi.jpg)

| Metric | Value |
|---|---|
| Mean NDVI 2016 | 0.3757 |
| Mean NDVI 2024 | 0.3779 |
| Mean NDVI difference (2024 - 2016) | +0.0021 |
| Vegetation ("green") loss from RGB k-means, 2016 to 2024 | 1.45 % of pixels |

A near-zero change in the *mean* does not mean nothing changed: the loss map below (NDVI loss mask,
threshold 0.7) shows many local patches of vegetation loss.

![NDVI loss mask at threshold 0.7](docs/results/ndvi_loss_threshold_0.7.jpg)

### Choice of NDVI threshold

Thresholds from 0.3 to 0.9 were compared. Lower values pull in non-vegetated noise; higher values start to
remove real vegetation, so 0.7 was used.

![Loss mask for thresholds 0.3-0.9](docs/results/threshold_comparison.jpg)

### RGB k-means as a cross-check

| 2016 | 2024 |
|---|---|
| ![k-means 2016](docs/results/kmeans_rgb_2016.jpg) | ![k-means 2024](docs/results/kmeans_rgb_2024.jpg) |

![Green loss map 2016 to 2024](docs/results/green_loss_2016_2024.jpg)

### Pipeline decisions and caveats

- **Final method:** raw, then dark-object subtraction, then homomorphic filtering, then adaptive denoising, then NDVI.
  Homomorphic filtering was added because illumination differences between the two dates produced false change.
- **Dropped from the proposal:** NDMI, because the imagery has no SWIR band.
- **Caveats:** the k-means "green" cluster share (about 60 %) depends on the clustering run, and no ground-truth
  validation is reported, so these numbers describe the pipeline's output, not validated land-cover change.
  Cloud and water masking is future work.

Full details are in [`TermProject_FinalReport.md`](TermProject_FinalReport.md) and [`PIPELINE_REPORT.md`](PIPELINE_REPORT.md).
The source imagery is not included because of its size.

## Requirements
- Windows 10/11
- Python 3.10+ (3.11+ recommended)
- Libraries: numpy, rasterio, pillow

## Setup
Open PowerShell in the project root and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install numpy rasterio pillow
```

## Input data
Place GeoTIFFs in `photos\` and name them like:

```
City_YYYY_Anything.tif
```

Band descriptions should include `B2`, `B3`, `B4`, `B8` for blue/green/red/NIR. If descriptions are missing, the scripts fall back to bands 1-4.

## Step-by-step pipeline (all images in a folder)
Run each stage from the project root:

```powershell
python scripts\01_data_check.py --input photos --out outputs\00_data_check.csv
python scripts\02_dark_object_subtraction.py --input photos --output outputs\01_dos
python scripts\03_homomorphic_filter.py --input outputs\01_dos --output outputs\02_homomorphic
python scripts\04_adaptive_noise_reduction.py --input outputs\02_homomorphic --output outputs\03_denoised
python scripts\05_features.py --input outputs\03_denoised --output outputs\04_features
```

Generate NDVI PNGs and NDVI difference maps:

```powershell
python scripts\09_ndvi_colormap_diff.py --features outputs\04_features --out-ndvi outputs\07_ndvi_png --out-diff outputs\08_ndvi_diff
```

Optional vegetation change analysis (loss/gain mask, summary CSV):

```powershell
python scripts\07_temporal_analysis.py --features outputs\04_features --bands outputs\03_denoised --output outputs\06_temporal
```

Optional PNG quicklooks for all TIFFs:

```powershell
python scripts\08_export_pngs.py --root . --output outputs\png
```

## One-shot NDVI diff for two images
Use the helper script to process two input images and output an NDVI difference map.

### Usage

```powershell
python scripts\13_run_ndvi_diff_pipeline.py \
  --image-a photos\Istanbul_2016_TOA.tif \
  --image-b photos\Istanbul_2024_TOA.tif \
  --output outputs\ndvi_diff_runs \
  --tag Istanbul_2016_2024
```

### Outputs
The script writes a new folder:

```
outputs\ndvi_diff_runs\Istanbul_2016_2024\
  a_dos.tif
  b_dos.tif
  a_homo.tif
  b_homo.tif
  a_denoise.tif
  b_denoise.tif
  a_ndvi.tif
  b_ndvi.tif
  a_ndvi.png
  b_ndvi.png
  ndvi_diff_istanbul_2016_2024.tif
  ndvi_diff_istanbul_2016_2024.png
```

### Notes
- The NDVI diff is computed as `NDVI_B - NDVI_A`.
- Adjust parameters like `--dos-percentile`, `--gamma-l`, `--gamma-h`, `--window`, or `--noise-percentile` if needed.

## MATLAB pipeline
MATLAB equivalents live in `matlab\`. These require the Mapping Toolbox (`readgeoraster`, `geotiffwrite`).

In MATLAB, add the folder to your path:

```matlab
addpath('matlab')
```

Then run the steps:

```matlab
step01_data_check('input','photos','out','outputs/00_data_check.csv');
step02_dark_object_subtraction('input','photos','output','outputs/01_dos');
step03_homomorphic_filter('input','outputs/01_dos','output','outputs/02_homomorphic');
step04_adaptive_noise_reduction('input','outputs/02_homomorphic','output','outputs/03_denoised');
step05_features('input','outputs/03_denoised','output','outputs/04_features');
step09_ndvi_colormap_diff('features','outputs/04_features','out_ndvi','outputs/07_ndvi_png','out_diff','outputs/08_ndvi_diff');
```

Optional steps:

```matlab
step07_temporal_analysis('features','outputs/04_features','bands','outputs/03_denoised','output','outputs/06_temporal');
step08_export_pngs('root','.', 'output','outputs/png');
```

### MATLAB one-shot NDVI diff for two images

```matlab
run_ndvi_diff_pipeline( ...
    'image_a','photos/Istanbul_2016_TOA.tif', ...
    'image_b','photos/Istanbul_2024_TOA.tif', ...
    'output','outputs/ndvi_diff_runs', ...
    'tag','Istanbul_2016_2024');
```

Outputs match the Python one-shot script layout.
