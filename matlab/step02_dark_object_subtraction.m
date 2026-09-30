function step02_dark_object_subtraction(varargin)
    p = inputParser;
    addParameter(p, 'input', 'photos');
    addParameter(p, 'output', 'outputs/01_dos');
    addParameter(p, 'percentile', 1.0);
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
        out = Common.dark_object_subtraction(data, args.percentile);
        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_dos.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end
