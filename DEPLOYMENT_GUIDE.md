# Hướng dẫn Triển khai aiDaptive Benchmark lên Google Cloud (GCP)

Tài liệu này hướng dẫn chi tiết cách thiết lập và chạy hệ thống Benchmark AI Server trên một máy ảo (VM) Ubuntu của Google Cloud Platform, kết hợp với quy trình đồng bộ mã nguồn qua GitHub.

---

## 1. Chuẩn bị Máy Ảo (VM) trên GCP

1. Truy cập **Google Cloud Console** -> **Compute Engine** -> **VM Instances**.
2. Nhấn **Create Instance**.
3. **Cấu hình đề xuất:**
   - **Tên:** `aidaptive-benchmark-server`
   - **Khu vực (Region):** Chọn khu vực gần với AI Server của bạn nhất (vd: `asia-southeast1` - Singapore).
   - **Machine Type:** Khuyên dùng `e2-medium` (2 vCPU, 4GB RAM).
   - **Boot Disk:** Ubuntu 22.04 LTS (Kích thước ổ cứng khuyên dùng: 20GB+).
   - **Firewall:** Tích chọn **Allow HTTP traffic** và **Allow HTTPS traffic**.
4. **Mở các cổng mạng (Port) cần thiết:**
   Vào **VPC network** -> **Firewall** và tạo quy tắc (Create Firewall Rule) mở các cổng TCP sau cho mọi IP (`0.0.0.0/0`):
   - `8443` (Cổng của ứng dụng Benchmark)
   - `3000` (Grafana Dashboard)
   - `8086` (InfluxDB)
   - `5432` (PostgreSQL - Tùy chọn nếu cần truy cập từ bên ngoài)

---

## 2. Cài đặt Môi trường trên Server (Chỉ làm 1 lần)

Đăng nhập vào VM của bạn thông qua SSH (nút SSH trên giao diện GCP) và chạy lần lượt các lệnh sau:

### 2.1 Cập nhật hệ thống và cài đặt Git, Python
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git python3-pip python3-venv screen -y
```

### 2.2 Cài đặt Docker & Docker Compose
```bash
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER
# CẬP NHẬT QUYỀN DOCKER: Bạn cần thoát SSH (gõ exit) và đăng nhập lại bằng SSH để áp dụng quyền Docker.
```

### 2.3 Cài đặt công cụ đo tải OHA
**Cài OHA:**
```bash
sudo wget https://github.com/hatoo/oha/releases/latest/download/oha-linux-amd64 -O /usr/local/bin/oha
sudo chmod +x /usr/local/bin/oha
```

---

## 3. Lấy Code về Server (Clone)

Lấy mã nguồn mà bạn đã đẩy lên GitHub về server:

```bash
# Thay THAY_TOKEN_CUA_BAN bằng mã ghp_... mà bạn đang có
git clone https://THAY_TOKEN_CUA_BAN@github.com/MrPhuocTan/aidaptive-benchmark.git

cd aidaptive-benchmark
```

---

## 4. Khởi chạy Ứng dụng

### 4.1 Khởi chạy các Database (PostgreSQL, InfluxDB, Grafana)
```bash
docker-compose up -d
```
*(Chờ khoảng 1-2 phút để các container khởi động hoàn toàn)*

### 4.2 Cài đặt thư viện Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.3 Chạy Ứng dụng trên nền (Background)
Để ứng dụng không bị tắt khi bạn đóng cửa sổ SSH, hãy dùng lệnh `screen`:

```bash
# Tạo một phiên làm việc mới tên là 'benchmark'
screen -S benchmark

# Đảm bảo bạn đang ở trong thư mục code và môi trường ảo đang bật
source .venv/bin/activate
python3 -m src
```

Lúc này ứng dụng đã chạy. Bạn có thể truy cập qua trình duyệt: `http://<IP_PUBLIC_CUA_SERVER>:8443`

👉 **Quan trọng:** Để thoát cửa sổ log mà **ứng dụng vẫn chạy**, bạn nhấn tổ hợp phím `Ctrl + A` sau đó nhấn `D`. 

---

## 5. Quy trình Đồng bộ Code Hằng Ngày (Push & Pull)

Mỗi khi bạn có sửa đổi code trên máy tính cá nhân (Macbook):

**Tại Macbook:**
```bash
git add .
git commit -m "Ghi chú thay đổi của bạn"
git push
```

**Tại Server GCP:**
1. Đăng nhập SSH vào Server.
2. Trở lại cửa sổ đang chạy ứng dụng:
   ```bash
   screen -r benchmark
   ```
3. Nhấn `Ctrl + C` để tạm dừng ứng dụng.
4. Kéo code mới về:
   ```bash
   git pull origin main
   ```
5. Chạy lại ứng dụng:
   ```bash
   python3 -m src
   ```
6. Nhấn `Ctrl + A` rồi `D` để thoát màn hình.

---

## 6. Xử lý Lỗi Cơ Bản

- **Không vào được web:** Kiểm tra xem đã mở Firewall port 8443 trên GCP chưa.
- **Lỗi Docker Permission Denied:** Do bạn quên đăng xuất và đăng nhập lại SSH sau khi chạy lệnh `usermod` ở phần 2.2.
- **Server bị đơ:** Nếu Server 2vCPU bị quá tải, hãy gõ `top` hoặc `htop` để kiểm tra tiến trình. Khởi động lại VM nếu cần thiết.
