# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Nguyễn Việt Thành |
| MSSV | 2A202602924 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/thanhnvhust514/K4-L3-DAY21-NguyenVietThanh-2A202602924-CI-CD-for-AI-Systems |
| Ngày lập báo cáo | 07/10/2026 |

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.710900 | 0.878 |
| 2 | 50 | 0.05 | 2 | 0.605128 | 0.846 |
| 3 | 200 | 0.2 | 5 | 0.703196 | 0.870 |

**Bộ siêu tham số đã chọn:** `n_estimators=100`, `learning_rate=0.1`, `max_depth=3`.

**Lý do:** Bộ này có F1 cao nhất và vượt ngưỡng 0.65. Accuracy cao nhất cũng thuộc cấu hình này. Cấu hình 50 cây với learning rate nhỏ đạt F1 thấp hơn; tăng lên 200 cây đồng thời tăng learning rate và độ sâu không cải thiện kết quả. Vì các tham số thay đổi cùng lúc, thí nghiệm chưa tách được ảnh hưởng riêng của từng tham số. Cấu hình được chọn dựa trên F1 thực tế.

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Lớp thu nhập trên 50K chỉ chiếm khoảng 24.8% dữ liệu. Mô hình luôn dự đoán thu nhập thấp vẫn có accuracy khoảng 0.752 nhưng bỏ sót toàn bộ lớp dương. F1 kết hợp precision và recall, phản ánh khả năng tìm đúng người thu nhập cao đồng thời hạn chế dự đoán nhầm. Lab dùng F1 nhị phân với lớp dương bằng 1; weighted F1 chịu ảnh hưởng mạnh của lớp đông, còn macro F1 đánh giá trung bình hai lớp, không trực tiếp đo mục tiêu lớp dương. Vì vậy Quality Gate kiểm tra F1 lớp dương đạt ít nhất 0.65 trước khi cho phép Release.

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| CI lỗi thiếu `pkg_resources`. | Môi trường sạch thiếu phụ thuộc mà MLflow 2.13 sử dụng. | Pin `setuptools==69.5.1` rồi chạy lại CI thành công. |
| SSH từ máy cá nhân bị timeout. | Kết nối đến cổng 22 chưa thông; chưa xác định chắc nguyên nhân. | Dùng EC2 Instance Connect; pipeline mở IP runner /32 tạm thời và xóa sau triển khai. |
| API cần đọc model trên S3. | EC2 ban đầu chưa được gắn instance profile. | Gắn role có quyền đọc `artifacts/*` và kiểm tra `/healthz`, `/score`. |

## 4. So Sánh Bước 2 và Bước 3

| | f1_score | accuracy |
|---|---|---|
| Bước 2: 22,361 mẫu | 0.710900 | 0.878 |
| Bước 3: 44,722 mẫu | 0.701422 | 0.874 |

**Nhận xét:** Trên cùng holdout 500 mẫu, F1 giảm khoảng 0.00948 và accuracy giảm 0.004; thêm dữ liệu không bảo đảm tăng chất lượng, dao động có thể liên quan đến holdout hữu hạn và dữ liệu cùng nguồn. Commit chỉ đổi con trỏ DVC đã tự kích hoạt đủ bốn job và triển khai model đạt ngưỡng lên EC2, xác nhận quy trình huấn luyện liên tục hoạt động.
