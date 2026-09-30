function step01_data_check(varargin)
    p = inputParser;
    addParameter(p, 'input', 'photos');
    addParameter(p, 'out', 'outputs/00_data_check.csv');
    parse(p, varargin{:});
    args = p.Results;

    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    rows = cell(numel(files), 7);
    for i = 1:numel(files)
        path = files{i};
        [data, ~, info] = Common.read_tif(path);
        [h, w, b] = size(data);
        names = Common.band_descriptions(info, b);
        name_str = strjoin(names, ',');
        dtype = class(data);
        dtype_str = strjoin(repmat({dtype}, 1, b), ',');
        [~, fname, ext] = fileparts(path);
        file = [fname ext];
        rows(i, :) = {file, num2str(w), num2str(h), num2str(b), Common.crs_string(info), dtype_str, name_str};
        disp([file, ': ', num2str(w), 'x', num2str(h), ', bands=', num2str(b), ', dtype=', dtype]);
    end

    Common.write_csv(args.out, rows, {'file', 'width', 'height', 'bands', 'crs', 'dtypes', 'band_names'});
    disp(['Wrote ', args.out]);
end
