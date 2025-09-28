# Railway PostgreSQL Database Backup

Bộ công cụ backup database PostgreSQL từ Railway về máy local.

## Các file được tạo

1. **`simple_backup.py`** - Script Python backup đơn giản (khuyến nghị)
2. **`railway_backup.py`** - Script backup nâng cao (cần PostgreSQL tools)
3. **`run_simple_backup.bat`** - Batch file chạy backup đơn giản
4. **`run_backup.bat`** - Batch file chạy backup nâng cao

## Cách sử dụng (Khuyến nghị - Đơn giản)

### Phương pháp 1: Backup đơn giản (chỉ cần Python)

1. **Chạy trực tiếp:**
   ```bash
   python simple_backup.py
   ```

2. **Hoặc chạy batch file:**
   ```bash
   run_simple_backup.bat
   ```

**Ưu điểm:**
- Chỉ cần Python (không cần cài PostgreSQL tools)
- Tự động cài đặt thư viện cần thiết
- Tạo cả file JSON và ZIP
- Dễ sử dụng

**Kết quả:**
- File JSON: `railway_backup_YYYYMMDD_HHMMSS.json`
- File ZIP: `railway_backup_YYYYMMDD_HHMMSS.zip`

### Phương pháp 2: Backup nâng cao (cần PostgreSQL tools)

1. **Cài đặt PostgreSQL client tools:**
   - Tải từ: https://www.postgresql.org/download/
   - Hoặc chỉ cài PostgreSQL client

2. **Chạy backup:**
   ```bash
   python railway_backup.py
   ```

**Ưu điểm:**
- Tạo file .sql chuẩn PostgreSQL
- Có thể restore trực tiếp bằng pg_restore
- Backup cả schema và data

## Thông tin kết nối Database

Script sử dụng thông tin từ Railway variables:

```
Host: centerbeam.proxy.rlwy.net
Port: 26191
Database: railway
Username: postgres
Password: qSNUGrxoEFLKrHkscytOjsacoCbByarc
```

## Các file backup được tạo

### JSON Backup (simple_backup.py)
- **Định dạng:** JSON với đầy đủ schema và data
- **Ưu điểm:** Dễ đọc, có thể xử lý bằng Python
- **Nhược điểm:** File size lớn hơn

### SQL Backup (railway_backup.py)
- **Định dạng:** PostgreSQL custom format
- **Ưu điểm:** Compact, restore nhanh
- **Nhược điểm:** Cần PostgreSQL tools

## Restore Database

### Từ JSON backup:
```python
import json

# Đọc backup
with open('railway_backup_YYYYMMDD_HHMMSS.json', 'r') as f:
    backup_data = json.load(f)

# Truy cập data
tables = backup_data['data']
schema = backup_data['schema']
```

### Từ SQL backup:
```bash
pg_restore -h localhost -U username -d database_name railway_backup_YYYYMMDD_HHMMSS.sql
```

## Troubleshooting

### Lỗi kết nối database:
1. Kiểm tra internet connection
2. Kiểm tra Railway database còn hoạt động
3. Kiểm tra credentials có thay đổi không

### Lỗi Python module:
```bash
pip install psycopg2-binary
```

### Lỗi PostgreSQL tools:
- Cài đặt PostgreSQL client từ trang chính thức
- Hoặc sử dụng `simple_backup.py`

## Lưu ý bảo mật

- **Không commit** các file backup lên Git
- **Lưu trữ an toàn** - backup chứa toàn bộ dữ liệu
- **Thay đổi password** sau khi backup nếu cần

## Tự động hóa

Có thể tạo scheduled task để backup định kỳ:

```bash
# Backup hàng ngày lúc 2:00 AM
schtasks /create /tn "Railway DB Backup" /tr "python C:\path\to\simple_backup.py" /sc daily /st 02:00
```

## Kiểm tra backup

Script sẽ hiển thị:
- Số lượng tables được backup
- Số lượng rows
- Kích thước file
- Tỷ lệ nén (với ZIP)

Ví dụ output:
```
✓ Backup completed successfully!

Backup Summary:
  Tables exported: 15
  Total rows: 1,234
  JSON file: railway_backup_20241001_143022.json (2,456,789 bytes, 2.34 MB)
  ZIP file: railway_backup_20241001_143022.zip (856,123 bytes, 0.82 MB)
  Compression ratio: 65.1%
```
