"""Cảnh báo box quá dài hoặc quá hẹp, tính theo kích thước pixel."""

import argparse
import math
from pathlib import Path

from pipeline.common import WARN, Dataset, Issue, load_config, parse_yolo_line, write_issues_csv


def check_aspect_ratio(dataset, max_ratio):
    if not math.isfinite(max_ratio) or max_ratio <= 1:
        raise ValueError("Tỉ lệ cạnh tối đa phải là số hữu hạn lớn hơn 1.")

    issues = []
    for image in dataset.image_files():
        size = dataset.image_size(image.stem)
        if size is None:
            continue
        image_width, image_height = size
        for line_number, line in dataset.read_label_lines(image.stem) or []:
            try:
                cls, _, _, width, height = parse_yolo_line(line)
            except (ValueError, OverflowError):
                continue
            if not (0 <= cls < len(dataset.classes) and 0 < width <= 1 and 0 < height <= 1):
                continue
            width_px, height_px = width * image_width, height * image_height
            short_side = min(width_px, height_px)
            if short_side < 1:
                continue  # BOX_TINY đã cảnh báo các cạnh dưới một pixel.
            ratio = max(width_px, height_px) / short_side
            if ratio > max_ratio:
                issues.append(Issue(
                    "aspect_ratio", WARN, "BOX_ASPECT_RATIO", image.stem,
                    f"cạnh dài / cạnh ngắn = {ratio:.2f} > {max_ratio:g}, cần xem lại box",
                    line=line_number,
                    extra={"ratio": round(ratio, 4), "width_px": round(width_px, 2),
                           "height_px": round(height_px, 2)},
                ))
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=Path("work/run/ds"))
    parser.add_argument("--out", type=Path, default=Path("work/bonus_aspect_ratio.csv"))
    parser.add_argument("--max-ratio", type=float, default=8.0)
    args = parser.parse_args()
    if not args.src.joinpath("images").is_dir():
        parser.error(f"không tìm thấy thư mục ảnh trong {args.src}")
    dataset = Dataset(args.src, load_config()["classes"])
    try:
        issues = check_aspect_ratio(dataset, args.max_ratio)
    except ValueError as error:
        parser.error(str(error))
    write_issues_csv(issues, args.out)
    print(f"{len(issues)} cảnh báo trên {len({issue.image for issue in issues})} ảnh → {args.out}")


if __name__ == "__main__":
    main()
