function step12_radiometric_normalization_pair(varargin)
    p = inputParser;
    addParameter(p, 'ref_2016', '');
    addParameter(p, 'ref_2024', '');
    addParameter(p, 'output', 'outputs/01_dos_norm_pair');
    addParameter(p, 'quantiles', 1024);
    parse(p, varargin{:});
    args = p.Results;

    if isempty(args.ref_2016) || isempty(args.ref_2024)
        error('ref_2016 and ref_2024 are required.');
    end

    Common.ensure_dir(args.output);
    [d16, R, info] = Common.read_tif(args.ref_2016);
    [d24, ~, ~] = Common.read_tif(args.ref_2024);

    out16 = zeros(size(d16), 'single');
    out24 = zeros(size(d24), 'single');

    for b = 1:size(d16, 3)
        band16 = d16(:,:,b);
        band24 = d24(:,:,b);
        ref_q = (single(band16) + single(band24)) / 2.0;
        out16(:,:,b) = match_histogram_quantiles(band16, ref_q, args.quantiles);
        out24(:,:,b) = match_histogram_quantiles(band24, ref_q, args.quantiles);
    end

    [~, name16] = fileparts(args.ref_2016);
    [~, name24] = fileparts(args.ref_2024);
    out16_path = fullfile(args.output, [name16 '_normpair.tif']);
    out24_path = fullfile(args.output, [name24 '_normpair.tif']);
    Common.write_tif(out16_path, out16, R, info, {});
    Common.write_tif(out24_path, out24, R, info, {});
    disp(['Wrote ', out16_path]);
    disp(['Wrote ', out24_path]);
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
