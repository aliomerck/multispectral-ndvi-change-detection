function step06_kmeans_segmentation(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/04_features');
    addParameter(p, 'output', 'outputs/05_segments');
    addParameter(p, 'k', 3);
    addParameter(p, 'iterations', 10);
    addParameter(p, 'sample', 200000);
    addParameter(p, 'seed', 0);
    parse(p, varargin{:});
    args = p.Results;

    Common.ensure_dir(args.output);
    files = Common.list_tifs(args.input);
    if isempty(files)
        disp(['No .tif files found in ', args.input]);
        return;
    end

    rng(args.seed);

    for i = 1:numel(files)
        path = files{i};
        [data, R, info] = Common.read_tif(path);
        ndvi = single(data(:,:,1));
        hue = single(data(:,:,2));
        if size(data, 3) >= 3
            ndmi = single(data(:,:,3));
            flat = [ndvi(:), hue(:), ndmi(:)];
        else
            flat = [ndvi(:), hue(:)];
        end
        mask = all(isfinite(flat), 2);
        flat = flat(mask, :);

        if size(flat, 1) > args.sample
            idx = randperm(size(flat, 1), args.sample);
            sample = flat(idx, :);
        else
            sample = flat;
        end

        mean_ = mean(sample, 1);
        std_ = std(sample, 0, 1);
        std_(std_ == 0) = 1;
        sample_n = (sample - mean_) ./ std_;

        centers = kmeans_custom(sample_n, args.k, args.iterations, args.seed);
        centers = centers .* std_ + mean_;

        flat_n = (flat - mean_) ./ std_;
        labels = assign_labels(flat_n, centers);
        labels = uint8(labels + 1);

        full_labels = zeros(numel(ndvi), 1, 'uint8');
        full_labels(mask) = labels;
        label_img = reshape(full_labels, size(ndvi));
        out = reshape(label_img, size(ndvi,1), size(ndvi,2), 1);

        [~, name] = fileparts(path);
        out_path = fullfile(args.output, [name '_segments.tif']);
        Common.write_tif(out_path, out, R, info, {'SEGMENTS'});
        disp(['Wrote ', out_path]);
    end
end

function centers = kmeans_custom(features, k, iterations, seed)
    rng(seed);
    centers = initialize_centers(features, k, seed);
    for iter = 1:iterations
        labels = assign_labels(features, centers);
        for i = 1:k
            mask = labels == (i - 1);
            if any(mask)
                centers(i, :) = mean(features(mask, :), 1);
            end
        end
    end
end

function centers = initialize_centers(features, k, seed)
    rng(seed);
    ndvi = features(:,1);
    hue = features(:,2);
    p = prctile(ndvi, [10 50 90]);
    h50 = prctile(hue, 50);
    if size(features, 2) >= 3
        ndmi = features(:,3);
        m = prctile(ndmi, [10 50 90]);
        centers = [p(1) h50 m(1); p(2) h50 m(2); p(3) h50 m(3)];
    else
        centers = [p(1) h50; p(2) h50; p(3) h50];
    end
    if k ~= 3
        idx = randperm(size(features,1), k);
        centers = features(idx, :);
    end
end

function labels = assign_labels(features, centers)
    dists = zeros(size(features,1), size(centers,1));
    for i = 1:size(centers,1)
        diff = features - centers(i, :);
        dists(:, i) = sum(diff.^2, 2);
    end
    [~, labels] = min(dists, [], 2);
    labels = labels - 1;
end
