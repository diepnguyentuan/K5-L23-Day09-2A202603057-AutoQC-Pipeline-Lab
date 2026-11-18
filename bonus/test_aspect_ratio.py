import pytest
from PIL import Image

from bonus.aspect_ratio import check_aspect_ratio
from pipeline.common import WARN, Dataset


def test_flags_tall_and_wide_boxes_in_pixels_and_preserves_line_numbers(tmp_path):
    dataset = Dataset(tmp_path, ["car"])
    dataset.images_dir.mkdir()
    dataset.labels_dir.mkdir()
    Image.new("RGB", (600, 200)).save(dataset.images_dir / "sample.png")
    dataset.label_path("sample").write_text(
        "0 .5 .5 .1 .3\n\n"  # box vuông 60 × 60 px
        "0 .5 .5 .5 .1\n"     # box ngang 300 × 20 px
        "0 .5 .5 .02 .9\n"   # box dọc 12 × 180 px
        "inf .5 .5 .5 .1\n" # dòng hỏng để check định dạng xử lý
        "0 .5 .5 .4 .15\n",  # đúng ngưỡng 8
        encoding="utf-8",
    )
    issues = check_aspect_ratio(dataset, max_ratio=8)
    assert [(i.severity, i.code, i.image, i.line, i.extra["ratio"]) for i in issues] == [
        (WARN, "BOX_ASPECT_RATIO", "sample", 3, 15.0),
        (WARN, "BOX_ASPECT_RATIO", "sample", 4, 15.0),
    ]


@pytest.mark.parametrize("threshold", [1, float("inf"), float("nan")])
def test_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="lớn hơn 1"):
        check_aspect_ratio(None, threshold)
