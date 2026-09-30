# MATLAB Pipeline

This folder contains MATLAB equivalents for the Python pipeline.

## Requirements
- MATLAB R2020a+ recommended
- Mapping Toolbox (for `readgeoraster` and `geotiffwrite`)

## Setup
In MATLAB:

```matlab
addpath('matlab')
```

## Step-by-step pipeline

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

## One-shot NDVI diff for two images

```matlab
run_ndvi_diff_pipeline( ...
    'image_a','photos/Istanbul_2016_TOA.tif', ...
    'image_b','photos/Istanbul_2024_TOA.tif', ...
    'output','outputs/ndvi_diff_runs', ...
    'tag','Istanbul_2016_2024');
```

## Notes
- If band descriptions are missing in the GeoTIFFs, the scripts fall back to bands 1–4.
- NDVI diff is computed as `NDVI_B - NDVI_A`.
