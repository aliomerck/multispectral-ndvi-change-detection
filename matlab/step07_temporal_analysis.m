function step07_temporal_analysis(varargin)
    p = inputParser;
    addParameter(p, 'features', 'outputs/04_features');
    addParameter(p, 'features_2016', '');
    addParameter(p, 'features_2024', '');
    addParameter(p, 'bands', 'outputs/03_denoised');
    addParameter(p, 'output', 'outputs/06_temporal');
    addParameter(p, 'ndvi_threshold', 0.3);
    addParameter(p, 'ndvi_max', []);
    addParameter(p, 'green_red_ratio', 1.05);
    addParameter(p, 'nir_red_ratio', 1.2);
    addParameter(p, 'ndwi_threshold', 0.0);
    addParameter(p, 'land_intersection', false);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    feat_files = Common.list_tifs(args.features);
    if isempty(feat_files) && isempty(args.features_2016) && isempty(args.features_2024)
        disp('Missing feature files.');
        return;
    end

    feat_map = containers.Map();
    for i = 1:numel(feat_files)
        [city, year] = parse_city_year(feat_files{i});
        if ~isempty(city)
            key = make_key(city, year);
            feat_map(key) = feat_files{i};
        end
    end

    if ~isempty(args.features_2016)
        extra = Common.list_tifs(args.features_2016);
        for i = 1:numel(extra)
            [city, year] = parse_city_year(extra{i});
            if ~isempty(city) && year == 2016
                feat_map(make_key(city, year)) = extra{i};
            end
        end
    end

    if ~isempty(args.features_2024)
        extra = Common.list_tifs(args.features_2024);
        for i = 1:numel(extra)
            [city, year] = parse_city_year(extra{i});
            if ~isempty(city) && year == 2024
                feat_map(make_key(city, year)) = extra{i};
            end
        end
    end

    keys = feat_map.keys;
    rows = {};

    for i = 1:numel(keys)
        key = keys{i};
        parts = strsplit(key, '|');
        city = parts{1};
        year = str2double(parts{2});
        other_year = 2024;
        if year == 2024
            other_year = 2016;
        end
        other_key = make_key(city, other_year);
        if ~isKey(feat_map, other_key)
            continue;
        end

        feat_path = feat_map(key);
        other_path = feat_map(other_key);

        [feat1, R, info] = Common.read_tif(feat_path);
        [feat2, ~, ~] = Common.read_tif(other_path);

        ndvi1 = feat1(:,:,1);
        ndvi2 = feat2(:,:,1);

        base1 = strip_suffix(feat_path);
        base2 = strip_suffix(other_path);
        base1 = strrep(base1, '_features', '');
        base2 = strrep(base2, '_features', '');
        bands1 = fullfile(args.bands, [base1 '.tif']);
        bands2 = fullfile(args.bands, [base2 '.tif']);

        if exist(bands1, 'file') && exist(bands2, 'file')
            [b1, g1, r1, n1] = load_bands(bands1);
            [b2, g2, r2, n2] = load_bands(bands2);
            ndwi1 = compute_ndwi(g1, n1);
            ndwi2 = compute_ndwi(g2, n2);
            water1 = ndwi1 > args.ndwi_threshold;
            water2 = ndwi2 > args.ndwi_threshold;
        else
            water1 = false(size(ndvi1));
            water2 = false(size(ndvi2));
            b1 = []; g1 = []; r1 = []; n1 = [];
            b2 = []; g2 = []; r2 = []; n2 = [];
        end

        land1 = ~water1;
        land2 = ~water2;
        if args.land_intersection
            land1 = land1 & land2;
            land2 = land1;
        end

        veg1 = (ndvi1 > args.ndvi_threshold) & land1;
        veg2 = (ndvi2 > args.ndvi_threshold) & land2;
        if ~isempty(args.ndvi_max)
            veg1 = veg1 & (ndvi1 <= args.ndvi_max);
            veg2 = veg2 & (ndvi2 <= args.ndvi_max);
        end
        if ~isempty(r1)
            gr1 = g1 ./ (r1 + 1e-6);
            nr1 = n1 ./ (r1 + 1e-6);
            veg1 = veg1 & (gr1 > args.green_red_ratio) & (nr1 > args.nir_red_ratio);
        end
        if ~isempty(r2)
            gr2 = g2 ./ (r2 + 1e-6);
            nr2 = n2 ./ (r2 + 1e-6);
            veg2 = veg2 & (gr2 > args.green_red_ratio) & (nr2 > args.nir_red_ratio);
        end

        total1 = sum(land1(:));
        total2 = sum(land2(:));
        pct1 = double(sum(veg1(:))) / max(total1, 1) * 100.0;
        pct2 = double(sum(veg2(:))) / max(total2, 1) * 100.0;
        delta = pct2 - pct1;

        rows(end+1, :) = {city, num2str(year), num2str(other_year), sprintf('%.2f', pct1), sprintf('%.2f', pct2), sprintf('%.2f', delta)}; %#ok<AGROW>

        diff = zeros(size(veg1), 'int8');
        diff(veg1 & ~veg2) = -1;
        diff(~veg1 & veg2) = 1;
        diff(water1 & water2) = 0;

        diff_path = fullfile(args.output, [city '_' num2str(year) '_' num2str(other_year) '_veg_diff.tif']);
        out = reshape(diff, size(diff,1), size(diff,2), 1);
        Common.write_tif(diff_path, out, R, info, {'VEG_DIFF'});
        disp(['Wrote ', diff_path]);
    end

    out_csv = fullfile(args.output, 'summary.csv');
    Common.write_csv(out_csv, rows, {'city', 'year_a', 'year_b', 'veg_pct_a', 'veg_pct_b', 'delta_pct'});
    disp(['Wrote ', out_csv]);
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

function base = strip_suffix(path)
    [~, base] = fileparts(path);
end

function ndwi = compute_ndwi(green, nir)
    green = single(green);
    nir = single(nir);
    denom = green + nir;
    ndwi = (green - nir) ./ (denom + 1e-6);
end

function [blue, green, red, nir] = load_bands(path)
    [data, ~, info] = Common.read_tif(path);
    bcount = size(data, 3);
    names = Common.band_descriptions(info, bcount);
    mapping = Common.band_indices_from_names(names);
    b_i = pick_index(mapping, 'B2', 1);
    g_i = pick_index(mapping, 'B3', 2);
    r_i = pick_index(mapping, 'B4', 3);
    n_i = pick_index(mapping, 'B8', 4);
    blue = data(:,:,b_i);
    green = data(:,:,g_i);
    red = data(:,:,r_i);
    nir = data(:,:,n_i);
end

function idx = pick_index(mapping, name, fallback)
    if isKey(mapping, name)
        idx = mapping(name);
    else
        idx = fallback;
    end
end
