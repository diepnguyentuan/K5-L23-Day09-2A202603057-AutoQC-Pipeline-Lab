"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    errors = [i for i in issues if i.severity == ERROR]
    if not errors:
        return []

    fixes = []
    removed_images = set()

    # 1. Xoá ảnh + nhãn cho các lỗi cấp ảnh
    for i in errors:
        if i.code.startswith("DUP_IMAGE_") or i.code in REMOVE_IMAGE_CODES:
            stem = i.image
            if stem in removed_images:
                continue
            removed_images.add(stem)
            img_p = ds.image_path(stem)
            lbl_p = ds.label_path(stem)
            before = img_p.name if img_p else stem
            if img_p and img_p.exists():
                img_p.unlink()
            if lbl_p.exists():
                lbl_p.unlink()
            fixes.append({
                "image": stem,
                "line": "",
                "action": "remove_image",
                "before": before,
                "after": "(đã xoá)",
            })

    # 2. Sửa data.yaml nếu BAD_CLASS_NAME (tối đa 1 lần)
    renamed_yaml = False
    for i in errors:
        if i.code == "BAD_CLASS_NAME" and not renamed_yaml:
            renamed_yaml = True
            data = {}
            if ds.yaml_path.exists():
                loaded = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            before_names = data.get("names", {})
            target_names = dict(enumerate(cfg["classes"]))
            data["names"] = target_names
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            fixes.append({
                "image": "data.yaml",
                "line": "",
                "action": "rename_classes",
                "before": str(before_names),
                "after": str(target_names),
            })

    # 3. Ghi nhận MISSING_LABEL_FILE (không tạo file nhãn)
    needs_label_seen = set()
    for i in errors:
        if i.code == "MISSING_LABEL_FILE":
            stem = i.image
            if stem in removed_images or stem in needs_label_seen:
                continue
            needs_label_seen.add(stem)
            fixes.append({
                "image": stem,
                "line": "",
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })

    # 4. Gom các lỗi sửa theo dòng theo từng file nhãn
    drop_by_stem = defaultdict(set)
    clip_by_stem = defaultdict(set)
    for i in errors:
        if i.image in removed_images or i.line is None:
            continue
        if i.code in DROP_CODES:
            drop_by_stem[i.image].add(i.line)
        elif i.code == "BOX_OUT_OF_IMAGE":
            clip_by_stem[i.image].add(i.line)

    for stem in sorted(set(drop_by_stem) | set(clip_by_stem)):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        raw_lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        drops = drop_by_stem[stem]
        clips = clip_by_stem[stem]
        new_lines = []
        changed = False

        for line_no, raw in enumerate(raw_lines, 1):
            if line_no in drops:
                changed = True
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": raw,
                    "after": "(đã xoá)",
                })
                continue

            if line_no in clips:
                changed = True
                try:
                    cls_id, x, y, w, h = parse_yolo_line(raw)
                except ValueError:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw,
                        "after": "(đã xoá)",
                    })
                    continue

                x1 = max(0.0, min(1.0, x - w / 2))
                y1 = max(0.0, min(1.0, y - h / 2))
                x2 = max(0.0, min(1.0, x + w / 2))
                y2 = max(0.0, min(1.0, y + h / 2))
                nw = x2 - x1
                nh = y2 - y1
                if nw <= 0.0 or nh <= 0.0:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw,
                        "after": "(đã xoá: ngoài ảnh)",
                    })
                    continue

                nx = (x1 + x2) / 2
                ny = (y1 + y2) / 2
                clipped = f"{cls_id} {nx:.6f} {ny:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(clipped)
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "clip_box",
                    "before": raw,
                    "after": clipped,
                })
                continue

            new_lines.append(raw)

        if changed:
            lp.write_text(("\n".join(new_lines) + "\n") if new_lines else "", encoding="utf-8")

    return fixes
