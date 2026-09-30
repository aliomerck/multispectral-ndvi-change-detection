function step10_color_istanbul_diff(varargin)
    p = inputParser;
    addParameter(p, 'input', 'outputs/06_temporal/Istanbul_2016_2024_veg_diff.tif');
    addParameter(p, 'output', 'outputs/06_temporal/Istanbul_veg_change_red_yellow.png');
    parse(p, varargin{:});
    args = p.Results;

    if ~exist(args.input, 'file')
        error(['Missing diff file: ', args.input]);
    end

    [diff, ~, ~] = Common.read_tif(args.input);
    diff = diff(:,:,1);

    [h, w] = size(diff);
    rgb = zeros(h, w, 3, 'uint8');
    loss = diff == -1;
    gain = diff == 1;

    rgb(:,:,1) = uint8(loss) * 255;
    rgb(:,:,1) = rgb(:,:,1) + uint8(gain) * 255;
    rgb(:,:,2) = uint8(gain) * 255;

    Common.ensure_dir(fileparts(args.output));
    imwrite(rgb, args.output);
    disp(['Wrote ', args.output]);
end
