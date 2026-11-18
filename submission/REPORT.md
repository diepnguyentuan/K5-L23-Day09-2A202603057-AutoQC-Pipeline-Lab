# Báo cáo Day 09 · Nguyễn Tuấn Điệp (2A202603057)

## 1. Kết luận

Lô này dừng ở **Hold** (mã thoát `10`). Từ 224 ảnh đầu vào, 22 ảnh bị loại ở cửa vào. Bản nháp `clean_v1` còn **202 ảnh và 748 box**. Sau lượt sửa tự động và duyệt mô phỏng 80/125 ảnh trong hàng đợi, lô còn **0 lỗi bắt buộc** và **38/202 ảnh (18,81%)** có cảnh báo chưa duyệt. Ngưỡng Hold là 10%. [Cửa vào](reports/01_intake.csv) · [Thống kê box](reports/class_stats.csv) · [Phán quyết](reports/08_summary.json)

## 2. Lỗi phát hiện và cách xử lý

Vòng đầu ghi 211 dòng, gồm 22 lỗi ở cửa vào trên 224 ảnh và 189 lỗi hoặc cảnh báo ở vòng kiểm nhãn trên 202 ảnh.

| Mã | Số dòng và số ảnh | Xử lý |
|---|---|---|
| `DUP_IMAGE_EXACT` | 8/224 ảnh | Loại ảnh trùng MD5. |
| `DUP_IMAGE_NEAR` | 4/224 ảnh | Loại ảnh gần trùng ở khoảng cách pHash ≤ 10. |
| `LEAK_TEST` | 5/224 ảnh | Loại ảnh gần trùng với tập đánh giá. |
| `BAD_SIZE` | 3/224 ảnh | Loại ảnh có cạnh ngắn dưới 250 px. |
| `CORRUPT_IMAGE` | 2/224 ảnh | Loại ảnh không đọc được. |
| `BAD_CLASS_NAME` | 2 mục trong `data.yaml` | Chuẩn hóa tên lớp. |
| `BOX_OUT_OF_IMAGE` | 8 dòng trên 8/202 ảnh | Cắt box về trong ảnh. |
| `DUP_BOX` | 7 dòng trên 7/202 ảnh | Xóa dòng box lặp cùng lớp. |
| `BAD_CLASS_ID` | 6 dòng trên 6/202 ảnh | Xóa dòng có ID ngoài 0–3. |
| `BOX_ZERO` | 4 dòng trên 4/202 ảnh | Xóa box có chiều rộng hoặc cao ≤ 0. |
| `BAD_FORMAT` | 3 dòng trên 3/202 ảnh | Xóa dòng nhãn sai định dạng. |
| `MISSING_LABEL_FILE` | 6/202 ảnh | Chuyển người gán nhãn. |
| `POSSIBLE_MISSING` | 53 dòng trên 52/202 ảnh | Người duyệt kiểm tra vật có thể bị sót. |
| `POSSIBLE_FALSE_POS` | 29 dòng trên 27/202 ảnh | Người duyệt kiểm tra box nghi gán thừa. |
| `POSSIBLE_LOOSE_BOX` | 28 dòng trên 24/202 ảnh | Người duyệt kiểm tra biên box. |
| `POSSIBLE_WRONG_CLASS` | 18 dòng trên 18/202 ảnh | Người duyệt xác nhận lớp. |
| `EMPTY_LABEL` | 12/202 ảnh | Người duyệt xác nhận ảnh nền hoặc thiếu nhãn. |
| `BOX_TINY` | 6 dòng trên 4/202 ảnh | Người duyệt xem box có cạnh ngắn dưới 12 px. |
| `BOX_HUGE` | 3 dòng trên 3/202 ảnh | Người duyệt xem box chiếm hơn 95% diện tích ảnh. |
| `CLASS_RARE` | 4 cảnh báo cấp lô | Bốn ID lạ biến mất sau khi xóa các dòng sai lớp. |

Nhật ký ghi 29 thao tác sửa gồm 20 lần xóa dòng, 8 lần cắt box và 1 lần sửa tên lớp. Sáu ảnh thiếu tệp nhãn được chuyển người gán. Ở `img_0020`, dòng 3 có ID `93` nên bị xóa. Ảnh này vẫn đứng đầu hàng đợi với **11,524 điểm** từ `FIXED_DROP_LINE`, nghi sai lớp và nghi thiếu nhãn. Phép tính là `2 + 3 × (1 + 0,9474) + 2 × (1 + 0,8408)`. Sáu ảnh `NEEDS_LABEL` theo sau, mỗi ảnh 10 điểm. [Danh sách lỗi vòng đầu](reports/02_error_list_v1.csv) · [Nhật ký sửa](reports/03_fixes.csv) · [Hàng đợi](reports/05_review_queue.csv)

Trong 123 cảnh báo ngữ nghĩa ở vòng 2, có **94 cảnh báo trên 74 ảnh** thuộc số ảnh đã duyệt mô phỏng. Lượt duyệt đi qua 18/18 cảnh báo sai lớp, 51/53 thiếu nhãn, 13/24 gán thừa và 12/28 box lỏng. [Vòng 2](reports/04_error_list_v2.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 3. Chọn ngưỡng

| Tham số | Khởi đầu → đã chọn | Precision / Recall trên tập calibration |
|---|---|---|
| `duplicates.phash_dist` | `2 → 10` | Gần trùng `1,00 / 0,50 → 1,00 / 0,67`. Trùng chính xác giữ `1,00 / 1,00`. |
| `second_opinion.conf` | `0.25 → 0.60` | Sai lớp `0,56 / 0,83 → 0,62 / 0,83`. Thiếu nhãn `0,50 / 1,00 → 0,57 / 1,00`. Box lỏng `0,29 / 0,40 → 0,20 / 0,20`. Gán thừa giữ `0,31 / 1,00`. |

Các mốc pHash 4–14 cho cùng kết quả trên 39 ảnh calibration. Mốc 10 bắt thêm cặp `img_0186`–`img_0061` trên lô raw. Hai ảnh cùng chụp cảnh người ngồi ghế trong công viên, khác phần khung hình. Với ngưỡng model 0,60, cảnh báo thiếu nhãn và sai lớp chính xác hơn trên tập calibration, đổi lại recall của box lỏng giảm. Tăng tiếp lên 0,70 hoặc 0,80 làm recall thiếu nhãn giảm còn 0,88 và 0,75.

Ở pHash 16, F1 của gần trùng là 0,91. Lên đến 20, recall của trùng chính xác tụt còn 0,33. Vì bước so với kho tham chiếu chạy trước bước tìm ảnh trùng trong lô, ngưỡng lớn còn có thể đổi mã lỗi được ghi. Cần xem các cặp ảnh cụ thể khi chọn ngưỡng cho lô khác. [Hai sweep](calibration/calibration_report.md) · [Cặp ảnh cửa vào](reports/01_intake.csv)

## 4. Thử gate và các trường hợp dễ lọt

```bash
python -m pipeline.run --budget 0 --work work/run_no_review --reports work/rep_nb --export-dir work/exp_nb
```

Ở lượt thử trên, máy xử lý 30 trong 36 lỗi bắt buộc qua 29 thao tác. Sáu lỗi thiếu tệp nhãn vẫn còn khi bỏ lượt duyệt, nên gate trả **Rework (20)**. Báo cáo thử nghiệm ghi `exported: null` và thư mục xuất không có manifest.

- Ở `img_0001`, model có một dự đoán `person` với `conf = 0.4175` và IoU tốt nhất dưới 0,30. Ngưỡng 0,60 loại dự đoán này trước bước so nhãn, nên cần xem ảnh để xác nhận có sót vật hay không.
- Ở `img_0024`, box `person` dòng 7 khớp với dự đoán cùng lớp ở IoU **0,5382**. Cặp này qua ngưỡng 0,50 nên không sinh cảnh báo box lỏng. QC vẫn có thể phát hiện biên box lệch khi soi ảnh.
- Sau khi bỏ các ảnh đã duyệt, vòng 3 còn 42 dòng cảnh báo trên 38 ảnh. Nhiều nhất là box lỏng (16 dòng) và nghi gán thừa (11 dòng). [Vòng 3](reports/07_error_list_v3.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 5. Huấn luyện trên Colab

Bốn lượt dùng **YOLO26n trên Tesla T4**, mỗi lượt 20 epoch, batch 16, cỡ ảnh 640. Cả hai biến thể dùng seed 0 và 1, chung 40 ảnh val và 100 ảnh test. `Raw` có 224 ảnh khi dựng bộ train và bộ đọc bỏ 11 ảnh có lỗi ảnh hoặc nhãn, còn **213 ảnh thực dùng**. `Clean` dùng đủ **202 ảnh**. Cột `#ảnh train` trong bảng tự sinh là số ảnh trước khi bộ đọc lọc. [Log Colab](results/colab_train.log) · [Kết quả tự sinh](results/comparison.md)

| Chỉ số | Raw (%) | Clean (%) |
|---|---:|---:|
| mAP50 | 72,58 ± 0,02 | 70,06 ± 2,46 |
| mAP50–95 | 51,17 ± 0,38 | 48,74 ± 0,83 |
| Precision | 76,35 ± 6,12 | 75,93 ± 0,33 |
| Recall | 64,90 ± 2,81 | 62,49 ± 1,93 |

*Trung bình ± độ lệch chuẩn mẫu qua hai seed.*

`Clean` thấp hơn `raw` về mAP50 ở cả hai seed. Chênh lệch là **0,76 điểm phần trăm** ở seed 0 và **4,27** ở seed 1. Chênh trung bình **2,52 điểm** xấp xỉ độ lệch **2,46 điểm** giữa hai seed của `clean`. Với mAP50–95, `clean` cũng thấp hơn ở cả hai seed, trung bình **2,43 điểm**. Hai seed đủ để thấy kết quả thay đổi theo lần chạy, còn quá ít để suy rộng cho lô khác.

- `Raw` vẫn chứa **5 ảnh gần trùng tập test** theo pHash. Các tệp có MD5 khác nhau. Cả năm ảnh đều qua bộ đọc train. Điều này có thể làm điểm `raw` cao hơn. Cần đo lại trên một tập test độc lập để xem chênh lệch còn giữ hay không. [Danh sách ảnh ở cửa vào](reports/01_intake.csv)
- `Truck` giảm rõ nhất, AP50 trung bình từ **64,85%** xuống **53,77%**. `Bus` tăng từ **69,49%** lên **70,33%**. Bản `clean` có 41 box `truck`, nên cần xem các box và ảnh của lớp này bị loại hoặc bị sửa ở bước nào, rồi kiểm tra theo cùng một tập đánh giá. Hai biến thể khác nhau cả về số ảnh và nhãn, nên lượt chạy này chưa tách được tác động của từng thay đổi. [Raw seed 0](results/raw_seed0.json) · [Raw seed 1](results/raw_seed1.json) · [Clean seed 0](results/clean_seed0.json) · [Clean seed 1](results/clean_seed1.json) · [Số box theo lớp](reports/class_stats.csv)

## 6. Quyết định, ghi chú AI và phần thưởng

Giữ **Hold** cho lô này. Nếu có thêm một lượt QC, hai ảnh ưu tiên là `img_0032` và `img_0210` vì còn cảnh báo thiếu nhãn. Với 202 ảnh, phải xử lý ít nhất 18 trong số 38 ảnh còn cảnh báo để giảm xuống tối đa 20/202 ảnh (9,90%), rồi chạy lại gate để kiểm tra lỗi bắt buộc. Ngân sách trong lần chạy nộp bài là 80 ảnh. [Phán quyết](reports/08_summary.json) · [Vòng 3](reports/07_error_list_v3.csv)

**Ghi chú AI**

- Yêu cầu AI soát bốn module theo đề, kiểm thử `--budget 0` và đối chiếu số liệu báo cáo với CSV, manifest và kết quả train.
- Kiểm lại bằng 83 test, chạy lại hai sweep cùng pipeline và so số liệu với tệp xuất. Bốn kết quả train đã được đối chiếu với mã băm của cấu hình và manifest.
- Một lệnh PowerShell do AI gợi ý đã dùng chuỗi nháy kép cho regex trích ảnh, làm PowerShell diễn giải phần ngoặc. Chuyển sang here-string nháy đơn rồi chạy lại.

**Check thưởng về tỷ lệ cạnh**

Chạy `python -m bonus.aspect_ratio --src work/run/ds` sau pipeline. Check đánh dấu box có cạnh dài chia cạnh ngắn lớn hơn 8 để QC xem lại. Trên bản sau duyệt có hai box bị đánh dấu, `img_0042` dòng 5 (9,58) và `img_0124` dòng 6 (9,11). Vật bị che khuất vẫn có thể có box hẹp hợp lệ. [Mã check](../bonus/aspect_ratio.py) · [Test](../bonus/test_aspect_ratio.py)
