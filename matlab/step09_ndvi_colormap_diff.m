function step09_ndvi_colormap_diff(varargin)
    p = inputParser;
    addParameter(p, 'features', 'outputs/04_features');
    addParameter(p, 'out_ndvi', 'outputs/07_ndvi_png');
    addParameter(p, 'out_diff', 'outputs/08_ndvi_diff');
    parse(p, varargin{:});
    args = p.Results;

    features = Common.list_tifs(args.features);
    if isempty(features)
        disp('No feature .tif files found.');
        return;
    end

    Common.ensure_dir(args.out_ndvi);
    Common.ensure_dir(args.out_diff);

    by_city_year = containers.Map();
    for i = 1:numel(features)
        path = features{i};
        [city, year] = parse_city_year(path);
        if ~isempty(city)
            by_city_year(make_key(city, year)) = path;
        end
    end

    stats = {};
    keys = by_city_year.keys;
    for i = 1:numel(keys)
        key = keys{i};
        parts = strsplit(key, '|');
        city = parts{1};
        year = str2double(parts{2});
        feat_path = by_city_year(key);
        [data, ~, ~] = Common.read_tif(feat_path);
        ndvi = single(data(:,:,1));
        rgb = Common.ndvi_colormap(ndvi);
        out_path = fullfile(args.out_ndvi, [city '_' num2str(year) '_ndvi.png']);
        imwrite(rgb, out_path);
        stats(end+1, :) = {city, num2str(year), sprintf('%.4f', mean(ndvi(~isnan(ndvi)), 'all'))}; %#ok<AGROW>
    end

    for i = 1:numel(keys)
        parts = strsplit(keys{i}, '|');
        city = parts{1};
        if isKey(by_city_year, make_key(city, 2016)) && isKey(by_city_year, make_key(city, 2024))
            [ndvi16, R, info] = Common.read_tif(by_city_year(make_key(city, 2016)));
            [ndvi24, ~, ~] = Common.read_tif(by_city_year(make_key(city, 2024)));
            diff = single(ndvi24(:,:,1)) - single(ndvi16(:,:,1));
            diff_tif = fullfile(args.out_diff, [city '_ndvi_diff_2024_2016.tif']);
            out = reshape(diff, size(diff,1), size(diff,2), 1);
            Common.write_tif(diff_tif, out, R, info, {'NDVI_DIFF'});
            diff_png = fullfile(args.out_diff, [city '_ndvi_diff_2024_2016.png']);
            imwrite(Common.diff_colormap(diff), diff_png);
            stats(end+1, :) = {city, '2024-2016', sprintf('%.4f', mean(diff(~isnan(diff)), 'all'))}; %#ok<AGROW>
        end
    end

    Common.write_csv(fullfile(args.out_diff, 'ndvi_stats.csv'), stats, {'city', 'year_or_diff', 'mean_ndvi'});
    disp(['Wrote NDVI PNGs to ', args.out_ndvi]);
    disp(['Wrote NDVI diffs to ', args.out_diff]);
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
