function run_ndvi_diff_pipeline(varargin)
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
