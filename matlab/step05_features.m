function step05_features(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/03_denoised');
    addParameter(p, 'output', 'outputs/04_features');
    addParameter(p, 'blue', 'B2');
    addParameter(p, 'green', 'B3');
    addParameter(p, 'red', 'B4');
    addParameter(p, 'nir', 'B8');
    addParameter(p, 'swir', 'B11');
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
        sw_i = pick_index(mapping, args.swir, 0);

        blue = data(:,:,b_i);
        green = data(:,:,g_i);
        red = data(:,:,r_i);
        nir = data(:,:,n_i);

        ndvi = Common.compute_ndvi(red, nir);
        hue = Common.compute_hue(red, green, blue, ~args.hue_rad);
        out = cat(3, ndvi, hue);
        if sw_i > 0 && sw_i <= bcount
            swir = data(:,:,sw_i);
            ndmi = Common.compute_ndvi(swir, nir);
            out = cat(3, out, ndmi);
        end
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_features.tif']);
        if size(out, 3) == 3
            Common.write_tif(out_path, out, R, info, {'NDVI', 'HUE', 'NDMI'});
        else
            Common.write_tif(out_path, out, R, info, {'NDVI', 'HUE'});
        end
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
