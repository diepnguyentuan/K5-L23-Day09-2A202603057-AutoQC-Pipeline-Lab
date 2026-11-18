"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401


def run(ds, cfg):
    c = cfg["label_format"]
    overflow_tol = c["overflow_tol"]
    dup_box_iou = c["dup_box_iou"]
    min_box_px = c["min_box_px"]
    max_box_frac = c["max_box_frac"]
    n_classes = len(ds.classes)
    issues = []

    for lf in ds.label_files():
        stem = lf.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue
        size = ds.image_size(stem)
        seen_boxes = []

        for line_no, ln in lines:
            try:
                cls_id, x, y, w, h = parse_yolo_line(ln)
            except ValueError as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, f"sai định dạng YOLO: {e}", line=line_no))
                continue

            if not (0 <= cls_id < n_classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"ID lớp {cls_id} ngoài 0..{n_classes - 1}", line=line_no))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"box có kích thước <= 0 ({w}, {h})", line=line_no))
                continue

            box = (x, y, w, h)
            overflow = max(-(x - w / 2), -(y - h / 2), (x + w / 2) - 1.0, (y + h / 2) - 1.0, 0.0)
            if overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn mép ảnh {overflow:.4f}",
                        line=line_no,
                        extra={"overflow": round(overflow, 6)},
                    )
                )

            if any(pc == cls_id and iou_xywh(pb, box) > dup_box_iou for pc, pb in seen_boxes):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, f"box trùng lặp cùng lớp {cls_id}", line=line_no))
            seen_boxes.append((cls_id, box))

            if size is not None:
                W, H = size
                short_px = min(w * W, h * H)
                if short_px < min_box_px:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"box quá nhỏ ({short_px:.1f}px < {min_box_px}px)", line=line_no))

            if w * h > max_box_frac:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"box phủ quá lớn ({w * h:.2%})", line=line_no))

    return issues
