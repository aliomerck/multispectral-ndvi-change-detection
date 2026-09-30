classdef Common
    methods(Static)
        function ensure_dir(path)
            if nargin < 1 || isempty(path)
                return;
            end
            if ~exist(path, 'dir')
                mkdir(path);
            end
        end

        function files = list_tifs(input_dir)
            if nargin < 1 || isempty(input_dir)
                files = {};
                return;
            end
            d = dir(fullfile(input_dir, '*.tif'));
            names = {d.name};
            [~, idx] = sort(lower(names));
            d = d(idx);
            files = fullfile({d.folder}, {d.name});
        end

        function [data, R, info] = read_tif(path)
            info = [];
            try
                info = geotiffinfo(path);
            catch
            end
            try
                [data, R] = readgeoraster(path);
            catch
                data = imread(path);
                R = [];
            end
            data = single(data);
            if ndims(data) == 2
                data = reshape(data, size(data,1), size(data,2), 1);
            end
        end

        function write_tif(path, data, R, info, descriptions)
            if nargin < 5
                descriptions = {};
            end
            Common.ensure_dir(fileparts(path));
            if nargin < 4
                info = [];
            end
            if isempty(R)
                error('No spatial referencing object for geotiffwrite.');
            end
            try
                if ~isempty(info) && isfield(info, 'GeoTIFFTags') && isfield(info.GeoTIFFTags, 'GeoKeyDirectoryTag')
                    geotiffwrite(path, data, R, 'GeoKeyDirectoryTag', info.GeoTIFFTags.GeoKeyDirectoryTag);
                else
                    geotiffwrite(path, data, R);
                end
            catch
                geotiffwrite(path, data, R);
            end
        end

        function names = band_descriptions(info, band_count)
            names = {};
            if nargin < 2
                band_count = 0;
            end
            if isempty(info)
                if band_count > 0
                    names = repmat({''}, 1, band_count);
                end
                return;
            end
            if isfield(info, 'Band') && ~isempty(info.Band)
                try
                    if isstruct(info.Band) && isfield(info.Band, 'Description')
                        descs = {info.Band.Description};
                        if ~isempty(descs)
                            names = descs;
                        end
                    end
                catch
                end
            end
            if isempty(names) && isfield(info, 'ImageDescription') && ischar(info.ImageDescription)
                txt = info.ImageDescription;
                if contains(txt, ',')
                    parts = strsplit(txt, ',');
                    names = strtrim(parts);
                end
            end
            if isempty(names) && band_count > 0
                names = repmat({''}, 1, band_count);
            end
            if band_count > 0 && numel(names) < band_count
                names = [names repmat({''}, 1, band_count - numel(names))];
            end
        end

        function mapping = band_indices_from_names(names)
            mapping = containers.Map();
            for i = 1:numel(names)
                name = names{i};
                if ~isempty(name)
                    mapping(name) = i;
                end
            end
        end

        function crs = crs_string(info)
            crs = '';
            if isempty(info)
                return;
            end
            if isfield(info, 'GeoTIFFCodes')
                if isfield(info.GeoTIFFCodes, 'PCS') && ~isempty(info.GeoTIFFCodes.PCS)
                    crs = num2str(info.GeoTIFFCodes.PCS);
                    return;
                end
                if isfield(info.GeoTIFFCodes, 'GCS') && ~isempty(info.GeoTIFFCodes.GCS)
                    crs = num2str(info.GeoTIFFCodes.GCS);
                    return;
                end
            end
        end

        function out = box_filter(img, k)
            if mod(k, 2) == 0
                error('k must be odd');
            end
            pad = floor(k / 2);
            padded = padarray(img, [pad pad], 'symmetric');
            csum = cumsum(cumsum(padded, 1), 2);
            csum = padarray(csum, [1 1], 0, 'pre');
            sum_ = csum(1+k:end, 1+k:end) - csum(1:end-k, 1+k:end) ...
                - csum(1+k:end, 1:end-k) + csum(1:end-k, 1:end-k);
            out = sum_ / (k * k);
        end

        function out = dark_object_subtraction(data, percentile)
            if nargin < 2
                percentile = 1.0;
            end
            out = zeros(size(data), 'single');
            bands = size(data, 3);
            for i = 1:bands
                band = single(data(:,:,i));
                haze = prctile(band(:), percentile);
                band = band - haze;
                band(band < 0) = 0;
                out(:,:,i) = band;
            end
        end

        function out = homomorphic_filter(band, gamma_l, gamma_h, c, d0)
            if nargin < 2, gamma_l = 0.5; end
            if nargin < 3, gamma_h = 1.5; end
            if nargin < 4, c = 1.0; end
            if nargin < 5, d0 = 30.0; end
            band = single(band);
            max_val = prctile(band(:), 99.9);
            if max_val <= 0
                out = band;
                return;
            end
            norm = band / max_val;
            log_img = log1p(norm);
            [rows, cols] = size(band);
            u = (0:rows-1) - rows / 2;
            v = (0:cols-1) - cols / 2;
            [U, V] = meshgrid(v, u);
            D2 = U.^2 + V.^2;
            H = (gamma_h - gamma_l) * (1 - exp(-c * D2 / (d0 * d0))) + gamma_l;
            fft_img = fftshift(fft2(log_img));
            filtered = H .* fft_img;
            inv_img = ifft2(ifftshift(filtered));
            out = expm1(real(inv_img));
            out = out * max_val;
            out(out < 0) = 0;
            out = single(out);
        end

        function out = adaptive_noise_reduction(band, window, noise_percentile)
            if nargin < 2, window = 7; end
            if nargin < 3, noise_percentile = 10.0; end
            band = single(band);
            mean_ = Common.box_filter(band, window);
            mean_sq = Common.box_filter(band .* band, window);
            var_ = mean_sq - mean_ .* mean_;
            var_(var_ < 0) = 0;
            noise_var = prctile(var_(:), noise_percentile);
            eps = 1e-6;
            out = band;
            mask = var_ > noise_var + eps;
            out(mask) = band(mask) - (noise_var ./ var_(mask)) .* (band(mask) - mean_(mask));
            out(~mask) = mean_(~mask);
            out(out < 0) = 0;
            out = single(out);
        end

        function ndvi = compute_ndvi(red, nir)
            red = single(red);
            nir = single(nir);
            denom = nir + red;
            ndvi = (nir - red) ./ (denom + 1e-6);
        end

        function hue = compute_hue(red, green, blue, degrees)
            if nargin < 4, degrees = true; end
            r = single(red);
            g = single(green);
            b = single(blue);
            max_val = max(max(r, g), b);
            max_val(max_val == 0) = 1;
            r = r ./ max_val;
            g = g ./ max_val;
            b = b ./ max_val;
            num = 0.5 * ((r - g) + (r - b));
            den = sqrt((r - g).^2 + (r - b) .* (g - b)) + 1e-6;
            theta = acos(max(min(num ./ den, 1), -1));
            hue = theta;
            hue(b > g) = 2 * pi - hue(b > g);
            if degrees
                hue = hue * 180 / pi;
            end
            hue = single(hue);
        end

        function write_csv(path, rows, header)
            Common.ensure_dir(fileparts(path));
            fid = fopen(path, 'w');
            if fid < 0
                error('Unable to open %s', path);
            end
            if ~isempty(header)
                fprintf(fid, '%s\n', strjoin(header, ','));
            end
            for i = 1:size(rows, 1)
                line = rows(i, :);
                for j = 1:numel(line)
                    if j > 1
                        fprintf(fid, ',');
                    end
                    fprintf(fid, '%s', line{j});
                end
                fprintf(fid, '\n');
            end
            fclose(fid);
        end

        function out = scale_to_uint8(arr, p_low, p_high)
            if nargin < 2, p_low = 2; end
            if nargin < 3, p_high = 98; end
            arr = single(arr);
            mask = isfinite(arr);
            if ~any(mask(:))
                out = zeros(size(arr), 'uint8');
                return;
            end
            vals = arr(mask);
            vmin = prctile(vals, p_low);
            vmax = prctile(vals, p_high);
            if vmax <= vmin
                vmax = vmin + 1.0;
            end
            out = (arr - vmin) ./ (vmax - vmin);
            out = max(min(out, 1), 0);
            out = uint8(out * 255);
        end

        function rgb = ndvi_colormap(ndvi)
            x = max(min((ndvi + 1.0) / 2.0, 1), 0);
            r = ones(size(x), 'single');
            r(x >= 0.5) = 1.0 - (x(x >= 0.5) - 0.5) * 2.0;
            g = zeros(size(x), 'single');
            g(x < 0.5) = x(x < 0.5) * 2.0;
            g(x >= 0.5) = 1.0;
            b = zeros(size(x), 'single');
            rgb = uint8(cat(3, r, g, b) * 255);
        end

        function rgb = diff_colormap(diff, vmin, vmax)
            if nargin < 2, vmin = -0.5; end
            if nargin < 3, vmax = 0.5; end
            x = (diff - vmin) ./ (vmax - vmin);
            x = max(min(x, 1), 0);
            r = zeros(size(x), 'single');
            b = zeros(size(x), 'single');
            g = ones(size(x), 'single');
            r(x > 0.5) = (x(x > 0.5) - 0.5) * 2.0;
            b(x < 0.5) = (0.5 - x(x < 0.5)) * 2.0;
            g = 1.0 - (abs(x - 0.5) * 2.0);
            rgb = uint8(cat(3, r, g, b) * 255);
        end
    end
end
