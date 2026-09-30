function step11_radiometric_normalization(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/01_dos');
    addParameter(p, 'output', 'outputs/01_dos_norm');
    addParameter(p, 'quantiles', 1024);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    by_city_year = containers.Map();
    for i = 1:numel(files)
        [city, year] = parse_city_year(files{i});
        if ~isempty(city)
            by_city_year(make_key(city, year)) = files{i};
        end
    end

    keys = by_city_year.keys;
    for i = 1:numel(keys)
        parts = strsplit(keys{i}, '|');
        city = parts{1};
        year = str2double(parts{2});
        if year ~= 2024
            continue;
        end
        ref_key = make_key(city, 2016);
        if ~isKey(by_city_year, ref_key)
            continue;
        end

        src_path = by_city_year(keys{i});
        ref_path = by_city_year(ref_key);
        [src_data, R, info] = Common.read_tif(src_path);
        [ref_data, ~, ~] = Common.read_tif(ref_path);

        out = zeros(size(src_data), 'single');
        for b = 1:size(src_data, 3)
            out(:,:,b) = match_histogram_quantiles(src_data(:,:,b), ref_data(:,:,b), args.quantiles);
        end

        [~, name] = fileparts(src_path);
        out_path = fullfile(args.output, [name '_norm.tif']);
        Common.write_tif(out_path, out, R, info, {});
        disp(['Wrote ', out_path]);
    end
end

function [city, year] = parse_city_year(path)
    [~, name] = fileparts(path);
    tokens = regexp(name, '^(?<city>.+)_(?<year>\d{4})_', 'names');
    if isempty(tokens)
        city = '';
        year = [];
        return;
    end
    city = tokens.city;
    year = str2double(tokens.year);
end

function key = make_key(city, year)
    key = [city '|' num2str(year)];
end

function matched = match_histogram_quantiles(source, reference, quantiles)
    src = single(source);
    ref = single(reference);
    mask_src = isfinite(src);
    mask_ref = isfinite(ref);
    if ~any(mask_src(:)) || ~any(mask_ref(:))
        matched = src;
        return;
    end
    qs = linspace(0.0, 1.0, quantiles);
    src_q = quantile(src(mask_src), qs);
    ref_q = quantile(ref(mask_ref), qs);
    src_q = max_accumulate(src_q);
    ref_q = max_accumulate(ref_q);
    flat = src(:);
    matched = interp1(src_q, ref_q, flat, 'linear', 'extrap');
    matched = reshape(matched, size(src));
    matched = single(matched);
end

function out = max_accumulate(x)
    out = x;
    for i = 2:numel(out)
        if out(i) < out(i-1)
            out(i) = out(i-1);
        end
    end
end
