function step03_homomorphic_filter(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/01_dos');
    addParameter(p, 'output', 'outputs/02_homomorphic');
    addParameter(p, 'gamma_l', 0.5);
    addParameter(p, 'gamma_h', 1.5);
    addParameter(p, 'c', 1.0);
    addParameter(p, 'd0', 30.0);
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
            out(:,:,b) = Common.homomorphic_filter(data(:,:,b), args.gamma_l, args.gamma_h, args.c, args.d0);
        end
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_homo.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end
