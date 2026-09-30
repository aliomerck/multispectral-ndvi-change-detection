function step04_adaptive_noise_reduction(varargin)
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
