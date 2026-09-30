function step08_export_pngs(varargin)
    p = inputParser;
    addParameter(p, 'root', '.');
    addParameter(p, 'output', 'outputs/png');
    parse(p, varargin{:});
    args = p.Results;

    root = fullfile(pwd, args.root);
    out_root = fullfile(root, args.output);

    tif_paths = [list_tifs_recursive(fullfile(root, 'photos')); list_tifs_recursive(fullfile(root, 'outputs'))];
    if isempty(tif_paths)
        disp('No .tif files found.');
        return;
    end

    for i = 1:numel(tif_paths)
        tif_path = tif_paths{i};
        rel = strrep(fileparts(tif_path), root, '');
        if startsWith(rel, filesep)
            rel = rel(2:end);
        end
        out_dir = fullfile(out_root, rel);
        export_tif(tif_path, out_dir);
        disp(['Exported ', tif_path, ' -> ', out_dir]);
    end
end

function export_tif(tif_path, out_dir)
    [data, ~, info] = Common.read_tif(tif_path);
    names = Common.band_descriptions(info, size(data, 3));
    mapping = Common.band_indices_from_names(names);

    Common.ensure_dir(out_dir);
    [~, stem] = fileparts(tif_path);
    count = size(data, 3);

    if count >= 3 && isKey(mapping, 'B2') && isKey(mapping, 'B3') && isKey(mapping, 'B4')
        b = Common.scale_to_uint8(data(:,:,mapping('B2')));
        g = Common.scale_to_uint8(data(:,:,mapping('B3')));
        r = Common.scale_to_uint8(data(:,:,mapping('B4')));
        rgb = cat(3, r, g, b);
        imwrite(rgb, fullfile(out_dir, [stem '_rgb.png']));
    elseif count >= 3
        r = Common.scale_to_uint8(data(:,:,1));
        g = Common.scale_to_uint8(data(:,:,2));
        b = Common.scale_to_uint8(data(:,:,3));
        rgb = cat(3, r, g, b);
        imwrite(rgb, fullfile(out_dir, [stem '_rgb.png']));
    end

    if count == 1
        band = Common.scale_to_uint8(data(:,:,1));
        imwrite(band, fullfile(out_dir, [stem '.png']));
    elseif count == 2
        name1 = safe_name(names, 1, 'band1');
        name2 = safe_name(names, 2, 'band2');
        imwrite(Common.scale_to_uint8(data(:,:,1)), fullfile(out_dir, [stem '_' lower(name1) '.png']));
        imwrite(Common.scale_to_uint8(data(:,:,2)), fullfile(out_dir, [stem '_' lower(name2) '.png']));
    elseif count > 3
        for i = 1:count
            name = safe_name(names, i, ['band' num2str(i)]);
            imwrite(Common.scale_to_uint8(data(:,:,i)), fullfile(out_dir, [stem '_' lower(name) '.png']));
        end
    end
end

function name = safe_name(names, idx, fallback)
    if idx <= numel(names) && ~isempty(names{idx})
        name = names{idx};
    else
        name = fallback;
    end
end

function files = list_tifs_recursive(root_dir)
    if ~exist(root_dir, 'dir')
        files = {};
        return;
    end
    d = dir(fullfile(root_dir, '**', '*.tif'));
    files = fullfile({d.folder}, {d.name});
end
