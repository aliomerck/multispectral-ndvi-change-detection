$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Running Method 1 pipeline (DOS -> Homomorphic -> Denoise -> NDVI) for Istanbul..."

python scripts/02_dark_object_subtraction.py --input photos --output outputs/istanbul_dos
python scripts/03_homomorphic_filter.py --input outputs/istanbul_dos --output outputs/istanbul_homo
python scripts/04_adaptive_noise_reduction.py --input outputs/istanbul_homo --output outputs/istanbul_denoise
python scripts/05_features.py --input outputs/istanbul_denoise --output outputs/istanbul_features_m1

Write-Host "Generating NDVI maps and diffs..."
python scripts/09_ndvi_colormap_diff.py --features outputs/istanbul_features_m1 --out-ndvi outputs/istanbul_png_m1 --out-diff outputs/istanbul_ndvi_diff_m1

Write-Host "Running vegetation change summary (NDVI>0.7, water masked)..."
python scripts/07_temporal_analysis.py `
  --features-2016 outputs/istanbul_features_m1 `
  --features-2024 outputs/istanbul_features_m1 `
  --bands outputs/istanbul_denoise `
  --output outputs/istanbul_results_m1_t07 `
  --ndvi-threshold 0.7 `
  --ndwi-threshold 0.0 `
  --land-intersection `
  --green-red-ratio 1.05 `
  --nir-red-ratio 1.2

Write-Host "Done."
