# Bước 2 với AWS

## Cấu hình của lab

- Region: `us-east-1`.
- S3 bucket: `income-lab21-257719179516-us-east-1`.
- DVC remote: `s3://income-lab21-257719179516-us-east-1/dvc`.
- Model được triển khai: `artifacts/current/model.joblib`.
- Báo cáo được triển khai: `artifacts/current/report.json`.

Ba file CSV đã được theo dõi bằng DVC và đẩy lên S3. File `.dvc/config`
không chứa credentials. AWS CLI đã được cấu hình trong bản WSL `Ubuntu`,
user Linux `thanhnv` (khác bản `Ubuntu-22.04`).

## Dùng DVC từ PowerShell trên máy hiện tại

Chạy tại thư mục gốc repo. DVC dùng credentials có sẵn trong Ubuntu:

```powershell
$env:AWS_SHARED_CREDENTIALS_FILE = '\\wsl.localhost\Ubuntu\home\thanhnv\.aws\credentials'
$env:AWS_CONFIG_FILE = '\\wsl.localhost\Ubuntu\home\thanhnv\.aws\config'
$env:AWS_DEFAULT_REGION = 'us-east-1'
.\.venv\Scripts\dvc.exe status -c
.\.venv\Scripts\dvc.exe push
```

Các đường dẫn này chỉ dùng trên máy cá nhân, không đặt vào `.dvc/config`.
Runner GitHub Actions và EC2 sử dụng cấu hình AWS riêng của chúng.

## EC2 cần chuẩn bị

Tạo instance tên `income-api`, Ubuntu Server 24.04 LTS (x86_64), trong
`us-east-1`, có public IPv4 và key pair SSH. Dùng tên đăng nhập `ubuntu`.
Security group cần cho phép SSH từ máy quản trị và runner CI, cùng TCP 8080
từ máy dùng để thử API. Cấu hình đường truy cập SSH cho runner trước khi chạy Release.

Trên EC2, cài môi trường ảo với các thư viện serving khớp môi trường huấn luyện:

```bash
sudo apt update
sudo apt install -y python3-venv
python3 -m venv ~/venv
~/venv/bin/pip install fastapi==0.111.0 uvicorn==0.29.0 scikit-learn==1.4.2 joblib==1.4.2 pandas==2.2.2 boto3==1.43.106
mkdir -p ~/src ~/models
```

Gắn IAM role cho EC2, cho phép `s3:GetObject` trên
`arn:aws:s3:::income-lab21-257719179516-us-east-1/artifacts/*`.
API sử dụng credentials của role qua Boto3.

Tạo service `/etc/systemd/system/income-api.service`:

```ini
[Unit]
Description=Income Model API
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment=ARTIFACT_BUCKET=income-lab21-257719179516-us-east-1
Environment=AWS_DEFAULT_REGION=us-east-1
ExecStart=/home/ubuntu/venv/bin/python /home/ubuntu/src/serve.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Sau đó chạy `sudo systemctl daemon-reload` và `sudo systemctl enable income-api`.
User SSH cần được chạy `sudo systemctl restart income-api` không cần nhập mật khẩu.
Chỉ khởi động API sau khi model đã được upload vào S3; workflow Release làm việc này.

## GitHub Actions Secrets

Vào Settings → Secrets and variables → Actions của repo, tạo:

| Secret | Nội dung |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key của danh tính được phép đọc dữ liệu và upload model lab |
| `AWS_SECRET_ACCESS_KEY` | Secret access key tương ứng |
| `AWS_SESSION_TOKEN` | Chỉ cần khi sử dụng temporary credentials |
| `ARTIFACT_BUCKET` | `income-lab21-257719179516-us-east-1` |
| `SERVER_HOST` | Public IPv4 của EC2 |
| `SERVER_USER` | `ubuntu` |
| `SERVER_SSH_KEY` | Private key SSH tương ứng public key được EC2 chấp nhận |

Workflow chạy bốn jobs: Unit Test → Train → Quality Gate → Release.
Train lưu model và report thành GitHub artifact. Chỉ Release mới upload vào
`artifacts/current/`, sau khi F1 đạt 0.65. Release copy `src/serve.py` lên EC2,
restart service và kiểm tra `/healthz`.

Trước khi triển khai, Release lấy IPv4 public của runner, thêm rule TCP 22
chỉ cho IP đó (`/32`) vào `sg-0a6755f4ddebc9425`, rồi lưu ID rule vừa tạo.
Bước cleanup dùng `always()` để thu hồi đúng rule đó khi các bước triển khai
thành công hoặc thất bại. Rule có sẵn được giữ nguyên. Khi runner bị tắt đột ngột
hoặc AWS không cho thu hồi, cần kiểm tra và xóa rule mang description của run.
Danh tính AWS của runner cần quyền `ec2:AuthorizeSecurityGroupIngress` và
`ec2:RevokeSecurityGroupIngress` trên Security Group này.
Chỉ chạy workflow sau khi chủ tài khoản đồng ý cơ chế mở SSH tạm thời này.

Workflow đã được kiểm tra cấu trúc và logic gate cục bộ. Cần EC2, Secrets và
một lần chạy GitHub Actions thực tế để xác nhận triển khai hoàn chỉnh.

## Tài liệu tham khảo

- [DVC với Amazon S3](https://dvc.org/doc/user-guide/data-management/remote-storage/amazon-s3)
- [Tạo EC2 bằng AWS Console](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-instance-wizard.html)
- [Policy S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html)
