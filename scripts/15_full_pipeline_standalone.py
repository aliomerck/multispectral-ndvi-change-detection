import argparse
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def read_tif(path):
    # Read as (bands, rows, cols) like rasterio expects.
    with rasterio.open(path) as ds:
        data = ds.read()
        profile = ds.profile
        descriptions = ds.descriptions
    return data, profile, descriptions


def write_tif(path, data, profile, dtype=None, descriptions=None):
    # Write GeoTIFF and keep geo info from the input.
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
    # Map band name -> 1-based index.
    mapping = {}
    for i, name in enumerate(descriptions, start=1):
        if name:
            mapping[name] = i
    return mapping


def box_filter(img, k):
    # Fast box filter using cumulative sums.
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
    # DOS: subtract a low percentile (haze) from each band.
    out = np.empty_like(data, dtype=np.float32)
    for i in range(data.shape[0]):
        band = data[i].astype(np.float32)
        haze = np.percentile(band, percentile)
        band = band - haze
        band[band < 0] = 0
        out[i] = band
    return out


def homomorphic_filter(band, gamma_l=0.5, gamma_h=1.5, c=1.0, d0=30):
    # Homomorphic filter in frequency domain.
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
    # Adaptive local noise reduction from local variance.
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
    # NDVI = (NIR - Red) / (NIR + Red)
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)
    denom = nir + red
    return (nir - red) / (denom + 1e-6)


def compute_hue(red, green, blue, degrees=True):
    # Hue angle from RGB (HSI style).
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
    hue = np.where(b <= g, theta, 2 * np.pi - theta)
    if degrees:
        hue = np.degrees(hue)
    return hue.astype(np.float32)

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


def save_mask(path, mask, color=(0, 255, 0)):
    h, w = mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[mask] = color
    Image.fromarray(rgb, mode="RGB").save(path)


def hist_equalize(band, bins=256):
    # Simple histogram equalization per band.
    band = band.astype(np.float32)
    mask = np.isfinite(band)
    if not mask.any():
        return band
    vals = band[mask]
    vmin, vmax = np.percentile(vals, [2, 98])
    if vmax <= vmin:
        return band
    scaled = (band - vmin) / (vmax - vmin)
    scaled = np.clip(scaled, 0, 1)
    hist, bin_edges = np.histogram(scaled[mask], bins=bins, range=(0.0, 1.0))
    cdf = hist.cumsum()
    cdf = cdf / max(cdf[-1], 1)
    lut = np.interp(scaled.ravel(), bin_edges[:-1], cdf)
    return lut.reshape(band.shape).astype(np.float32)


def kmeans(features, k=3, iterations=10, seed=0):
    # Plain k-means, no fancy init.
    rng = np.random.default_rng(seed)
    idx = rng.choice(features.shape[0], size=k, replace=False)
    centers = features[idx].astype(np.float32)
    for _ in range(iterations):
        dists = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(dists, axis=1)
        for i in range(k):
            mask = labels == i
            if np.any(mask):
                centers[i] = features[mask].mean(axis=0)
    return labels, centers


def process_pipeline(path, args, out_dir, tag):
    data, profile, descriptions = read_tif(path)

    # DOS (haze removal)
    dos = dark_object_subtraction(data, percentile=args.dos_percentile)
    write_tif(out_dir / f"{tag}_dos.tif", dos, profile, dtype="float32", descriptions=descriptions)

    # Homomorphic filter (illumination correction)
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
    write_tif(out_dir / f"{tag}_homo.tif", homo, profile, dtype="float32", descriptions=descriptions)

    # Denoise (adaptive)
    denoise_bands = []
    for i in range(homo.shape[0]):
        denoise_bands.append(
            adaptive_noise_reduction(
                homo[i], window=args.window, noise_percentile=args.noise_percentile
            )
        )
    denoise = np.stack(denoise_bands, axis=0)
    write_tif(
        out_dir / f"{tag}_denoise.tif",
        denoise,
        profile,
        dtype="float32",
        descriptions=descriptions,
    )

    # NDVI from corrected bands
    mapping = band_indices_from_descriptions(descriptions)
    r_i = mapping.get(args.red, 3) - 1 if args.red in mapping else 2
    n_i = mapping.get(args.nir, 4) - 1 if args.nir in mapping else 3
    ndvi = compute_ndvi(denoise[r_i], denoise[n_i])
    write_tif(
        out_dir / f"{tag}_ndvi.tif",
        ndvi[np.newaxis, :, :],
        profile,
        dtype="float32",
        descriptions=["NDVI"],
    )
    save_png(out_dir / f"{tag}_ndvi.png", ndvi_colormap(ndvi))

    return ndvi, profile, descriptions


def kmeans_rgb(path, args, out_dir, tag):
    data, profile, descriptions = read_tif(path)
    mapping = band_indices_from_descriptions(descriptions)
    r_i = mapping.get(args.red, 3) - 1 if args.red in mapping else 2
    g_i = mapping.get(args.green, 2) - 1 if args.green in mapping else 1
    b_i = mapping.get(args.blue, 1) - 1 if args.blue in mapping else 0

    # Equalize to make colors pop more
    red = hist_equalize(data[r_i])
    green = hist_equalize(data[g_i])
    blue = hist_equalize(data[b_i])

    flat = np.stack([red.ravel(), green.ravel(), blue.ravel()], axis=1)
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

    full_labels = np.zeros(red.size, dtype=np.uint8)
    full_labels[mask] = labels + 1
    label_img = full_labels.reshape(red.shape)

    write_tif(
        out_dir / f"{tag}_rgb_kmeans.tif",
        label_img[np.newaxis, :, :],
        profile,
        dtype="uint8",
        descriptions=["KMEANS"],
    )

    palette = np.array(
        [
            [0, 0, 0],
            [0, 128, 0],
            [255, 215, 0],
            [0, 0, 255],
            [255, 0, 0],
            [128, 0, 128],
        ],
        dtype=np.uint8,
    )
    vis = palette[np.clip(label_img, 0, len(palette) - 1)]
    Image.fromarray(vis, mode="RGB").save(out_dir / f"{tag}_rgb_kmeans.png")

    # Pick the greenish cluster using mean green ratio on raw bands
    red_raw = data[r_i].astype(np.float32)
    green_raw = data[g_i].astype(np.float32)
    blue_raw = data[b_i].astype(np.float32)
    denom = red_raw + green_raw + blue_raw + 1e-6
    g_ratio = green_raw / denom

    clusters = np.unique(label_img)
    clusters = clusters[clusters > 0]
    best = None
    best_g = -1
    for c in clusters:
        cmask = label_img == c
        if not cmask.any():
            continue
        g_mean = float(g_ratio[cmask].mean())
        if g_mean > best_g:
            best_g = g_mean
            best = c

    green_mask = label_img == best
    write_tif(
        out_dir / f"{tag}_green_mask.tif",
        green_mask[np.newaxis, :, :].astype(np.uint8),
        profile,
        dtype="uint8",
        descriptions=["GREEN_MASK"],
    )
    save_mask(out_dir / f"{tag}_green_mask.png", green_mask, color=(0, 255, 0))

    return green_mask


def kmeans_hue(red, green, blue, profile, out_dir, tag, k=3, iterations=10, seed=0):
    hue = compute_hue(red, green, blue, degrees=True)
    flat = hue.ravel().astype(np.float32)
    mask = np.isfinite(flat)
    flat = flat[mask][:, None]

    labels, _ = kmeans(flat, k=k, iterations=iterations, seed=seed)
    full_labels = np.zeros(hue.size, dtype=np.uint8)
    full_labels[mask] = labels + 1
    label_img = full_labels.reshape(hue.shape)

    write_tif(
        out_dir / f"{tag}_hue_kmeans.tif",
        label_img[np.newaxis, :, :],
        profile,
        dtype="uint8",
        descriptions=["HUE_KMEANS"],
    )

    palette = np.array(
        [
            [0, 0, 0],
            [128, 0, 128],
            [0, 150, 255],
            [255, 200, 0],
            [0, 200, 100],
            [200, 0, 0],
        ],
        dtype=np.uint8,
    )
    vis = palette[np.clip(label_img, 0, len(palette) - 1)]
    Image.fromarray(vis, mode="RGB").save(out_dir / f"{tag}_hue_kmeans.png")


def main():
    parser = argparse.ArgumentParser(description="Standalone full pipeline for Istanbul pairs.")
    parser.add_argument("--image-2016", default="photos/Istanbul_2016_TOA.tif")
    parser.add_argument("--image-2024", default="photos/Istanbul_2024_TOA.tif")
    parser.add_argument("--output", default="outputs/standalone_run")
    parser.add_argument("--blue", default="B2")
    parser.add_argument("--green", default="B3")
    parser.add_argument("--red", default="B4")
    parser.add_argument("--nir", default="B8")
    parser.add_argument("--dos-percentile", type=float, default=1.0)
    parser.add_argument("--gamma-l", type=float, default=0.5)
    parser.add_argument("--gamma-h", type=float, default=1.5)
    parser.add_argument("--c", type=float, default=1.0)
    parser.add_argument("--d0", type=float, default=30.0)
    parser.add_argument("--window", type=int, default=7)
    parser.add_argument("--noise-percentile", type=float, default=10.0)
    parser.add_argument("--ndvi-thresh", type=float, default=0.7)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--sample", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    out_dir = Path(args.output)
    ensure_dir(out_dir)

    path16 = Path(args.image_2016)
    path24 = Path(args.image_2024)
    if not path16.exists() or not path24.exists():
        raise FileNotFoundError("Missing input images.")

    ndvi16, profile, _ = process_pipeline(path16, args, out_dir, "2016")
    ndvi24, _, _ = process_pipeline(path24, args, out_dir, "2024")

    # NDVI diff map (2024 - 2016)
    diff = ndvi24.astype(np.float32) - ndvi16.astype(np.float32)
    write_tif(
        out_dir / "ndvi_diff_2024_2016.tif",
        diff[np.newaxis, :, :],
        profile,
        dtype="float32",
        descriptions=["NDVI_DIFF"],
    )
    save_png(out_dir / "ndvi_diff_2024_2016.png", diff_colormap(diff))

    # Thresholded loss at 0.7 (only loss)
    veg16 = ndvi16 >= args.ndvi_thresh
    veg24 = ndvi24 >= args.ndvi_thresh
    loss = veg16 & (~veg24)
    write_tif(
        out_dir / f"ndvi_loss_thresh_{args.ndvi_thresh:.1f}.tif",
        loss[np.newaxis, :, :].astype(np.uint8),
        profile,
        dtype="uint8",
        descriptions=["NDVI_LOSS"],
    )
    save_mask(out_dir / f"ndvi_loss_thresh_{args.ndvi_thresh:.1f}.png", loss, color=(255, 0, 0))

    # K-means on RGB and green loss
    green16 = kmeans_rgb(path16, args, out_dir, "2016")
    green24 = kmeans_rgb(path24, args, out_dir, "2024")

    # K-means on hue only (from corrected bands)
    data16, profile16, desc16 = read_tif(out_dir / "2016_denoise.tif")
    data24, profile24, desc24 = read_tif(out_dir / "2024_denoise.tif")
    mapping16 = band_indices_from_descriptions(desc16)
    mapping24 = band_indices_from_descriptions(desc24)
    r16 = data16[mapping16.get(args.red, 3) - 1 if args.red in mapping16 else 2]
    g16 = data16[mapping16.get(args.green, 2) - 1 if args.green in mapping16 else 1]
    b16 = data16[mapping16.get(args.blue, 1) - 1 if args.blue in mapping16 else 0]
    r24 = data24[mapping24.get(args.red, 3) - 1 if args.red in mapping24 else 2]
    g24 = data24[mapping24.get(args.green, 2) - 1 if args.green in mapping24 else 1]
    b24 = data24[mapping24.get(args.blue, 1) - 1 if args.blue in mapping24 else 0]

    kmeans_hue(r16, g16, b16, profile16, out_dir, "2016", k=args.k, iterations=args.iterations, seed=args.seed)
    kmeans_hue(r24, g24, b24, profile24, out_dir, "2024", k=args.k, iterations=args.iterations, seed=args.seed)

    green_loss = green16 & (~green24)
    write_tif(
        out_dir / "green_loss_2016_2024.tif",
        green_loss[np.newaxis, :, :].astype(np.uint8),
        profile,
        dtype="uint8",
        descriptions=["GREEN_LOSS"],
    )
    save_mask(out_dir / "green_loss_2016_2024.png", green_loss, color=(0, 255, 0))

    p16 = green16.mean() * 100.0
    p24 = green24.mean() * 100.0
    loss_pct = green_loss.mean() * 100.0
    summary = (
        f"Green pct 2016: {p16:.2f}%\n"
        f"Green pct 2024: {p24:.2f}%\n"
        f"Green loss pct (2016->2024): {loss_pct:.2f}%\n"
    )
    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary.strip())


if __name__ == "__main__":
    main()
