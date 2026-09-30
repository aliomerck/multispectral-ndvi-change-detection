import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from common import band_indices_from_descriptions, ensure_dir, list_tifs, read_tif, write_tif


def kmeans(features, k=3, iterations=10, seed=0):
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


def scale_uint8(arr, p_low=2, p_high=98):
    arr = arr.astype(np.float32)
    mask = np.isfinite(arr)
    if not mask.any():
        return np.zeros(arr.shape, dtype=np.uint8)
    vmin, vmax = np.percentile(arr[mask], [p_low, p_high])
    if vmax <= vmin:
        vmax = vmin + 1.0
    out = (arr - vmin) / (vmax - vmin)
    out = np.clip(out, 0, 1)
    return (out * 255).astype(np.uint8)


def hist_equalize(band, bins=256):
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


def save_rgb(path, r, g, b):
    rgb = np.stack([r, g, b], axis=2)
    Image.fromarray(rgb, mode="RGB").save(path)


def save_mask(path, mask, color=(0, 255, 0)):
    h, w = mask.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[mask] = color
    Image.fromarray(rgb, mode="RGB").save(path)


def pick_rgb_indices(descriptions):
    mapping = band_indices_from_descriptions(descriptions)
    b_i = mapping.get("B2", 1) - 1 if "B2" in mapping else 0
    g_i = mapping.get("B3", 2) - 1 if "B3" in mapping else 1
    r_i = mapping.get("B4", 3) - 1 if "B4" in mapping else 2
    return r_i, g_i, b_i


def main():
    parser = argparse.ArgumentParser(
        description="K-means clustering on RGB bands and extract greenish cluster."
    )
    parser.add_argument("--input", default="photos", help="Input folder with .tif files")
    parser.add_argument("--output", default="outputs/rgb_kmeans", help="Output folder")
    parser.add_argument("--k", type=int, default=3, help="Number of clusters")
    parser.add_argument("--iterations", type=int, default=10, help="K-means iterations")
    parser.add_argument("--sample", type=int, default=200000, help="Sample size for fitting")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--match", default=None, help="Only process files containing this text")
    parser.add_argument(
        "--green-min",
        type=float,
        default=0.36,
        help="Minimum normalized green ratio for the green mask",
    )
    parser.add_argument(
        "--green-delta",
        type=float,
        default=0.03,
        help="Minimum dominance of green over red/blue in normalized space",
    )
    args = parser.parse_args()

    ensure_dir(args.output)
    files = list_tifs(args.input)
    if not files:
        print("No .tif files found in", args.input)
        return

    for path in files:
        if args.match and args.match.lower() not in Path(path).name.lower():
            continue
        data, profile, descriptions = read_tif(path)
        r_i, g_i, b_i = pick_rgb_indices(descriptions)
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

        # Pick the "greenish" cluster based on center strength in green channel.
        green_score = centers[:, 1] - 0.5 * (centers[:, 0] + centers[:, 2])
        green_idx = int(np.argmax(green_score))
        # Refine with per-pixel normalized green dominance.
        denom = red + green + blue + 1e-6
        r_n = red / denom
        g_n = green / denom
        b_n = blue / denom
        green_dom = (g_n - np.maximum(r_n, b_n)) >= args.green_delta
        green_mask = (label_img == (green_idx + 1)) & (g_n >= args.green_min) & green_dom

        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)

        out_tif = out_dir / f"{Path(path).stem}_rgb_kmeans.tif"
        write_tif(out_tif, label_img[np.newaxis, :, :], profile, dtype="uint8", descriptions=["KMEANS"])

        # Cluster map visualization (fixed palette).
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
        Image.fromarray(vis, mode="RGB").save(out_dir / f"{Path(path).stem}_rgb_kmeans.png")

        # Greenish mask output.
        green_tif = out_dir / f"{Path(path).stem}_green_mask.tif"
        write_tif(
            green_tif,
            green_mask[np.newaxis, :, :].astype(np.uint8),
            profile,
            dtype="uint8",
            descriptions=["GREEN_MASK"],
        )
        save_mask(out_dir / f"{Path(path).stem}_green_mask.png", green_mask, color=(0, 255, 0))

        # RGB quicklook for reference.
        save_rgb(
            out_dir / f"{Path(path).stem}_rgb.png",
            scale_uint8(red),
            scale_uint8(green),
            scale_uint8(blue),
        )

        print("Wrote", out_tif)
        print("Wrote", green_tif)


if __name__ == "__main__":
    main()
