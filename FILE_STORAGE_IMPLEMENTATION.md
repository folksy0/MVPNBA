# NBA MVP System - User File Storage Implementation

## Overview

Sistem NBA MVP telah diperbarui dengan implementasi penyimpanan file yang terorganisir berdasarkan user dan urutan upload. Sistem ini memastikan setiap user memiliki direktori terpisah dan file disimpan dengan urutan yang jelas, sementara database SQLite hanya menyimpan metadata file dan data pengguna.

## Struktur Penyimpanan File

### Direktori Structure
```
uploads/
├── user_1/
│   ├── upload_0001_20250615_143022.csv
│   ├── upload_0002_20250615_144515.csv
│   └── upload_0003_20250615_150123.csv
├── user_2/
│   ├── upload_0001_20250615_151245.csv
│   └── upload_0002_20250615_152030.csv
└── user_3/
    └── upload_0001_20250615_153412.csv
```

### Konvensi Penamaan File
- Format: `upload_{order:04d}_{timestamp}.{extension}`
- Contoh: `upload_0001_20250615_143022.csv`
- Order: 4-digit upload sequence per user (0001, 0002, dst.)
- Timestamp: YYYYMMDD_HHMMSS format
- Extension: File extension asli (csv, xlsx, dll.)

## Database Schema

### Tabel `file_uploads` (Baru)
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    upload_order INTEGER,
    file_type TEXT DEFAULT 'csv',
    status TEXT DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (session_id) REFERENCES upload_sessions (id)
);
```

### Tabel yang Diperbarui
- `players`: Ditambahkan kolom `uploaded_by`
- `statistics`: Ditambahkan kolom `uploaded_by`
- `mvp_scores`: Ditambahkan kolom `calculated_by`
- `upload_sessions`: Ditambahkan kolom `user_id`

## Fitur-Fitur Baru

### 1. User-Specific File Storage
- Setiap user memiliki direktori terpisah (`uploads/user_{user_id}/`)
- File tidak dapat diakses oleh user lain
- Isolasi data antar pengguna

### 2. Upload Ordering System
- File diberi nomor urut berdasarkan urutan upload per user
- Tracking upload order untuk manajemen file yang lebih baik
- History upload yang terorganisir

### 3. File Management
- Download file upload sebelumnya
- Delete file yang tidak dibutuhkan
- View upload history dengan detail
- Automatic cleanup (menyimpan 10 file terbaru per user)

### 4. Enhanced Security
- File validation yang lebih ketat
- Path traversal protection
- Size dan type validation
- Secure filename generation

## API Endpoints Baru

### Upload History
```
GET /upload_history
- Menampilkan history upload user
- Pagination support
- File size dan status information
```

### File Download
```
GET /download_upload/<upload_id>
- Download file berdasarkan ID
- User access control
- Activity logging
```

### File Delete
```
POST /delete_upload/<upload_id>
- Hapus file upload
- Soft delete with cleanup
- Activity logging
```

## Manajemen Storage

### Automatic Cleanup
- Sistem otomatis menyimpan 10 file terbaru per user
- File lama dihapus secara otomatis
- Configurable retention policy

### Storage Monitoring
- Track total storage per user
- File size monitoring
- Usage statistics

### File Status Tracking
- `uploaded`: File berhasil diupload
- `processed`: Data berhasil diproses ke database
- `failed`: Processing gagal
- `error`: System error

## Implementasi Keamanan

### 1. File Validation
```python
def validate_file_upload(file, allowed_extensions=['csv'], max_size_mb=16):
    # Extension validation
    # File size validation  
    # MIME type checking
    # Malicious content scanning
```

### 2. Path Security
```python
def get_user_upload_directory(user_id):
    # Sanitized path generation
    # Directory isolation
    # Permission management
```

### 3. Access Control
- User dapat hanya mengakses file miliknya sendiri
- Admin dapat melihat semua upload (read-only)
- Role-based file access

## Database Storage Strategy

### File Content vs Metadata
- **Database menyimpan**: Path file, metadata, user info, upload info
- **File system menyimpan**: Konten file aktual (CSV data)
- **Keuntungan**: Database tetap lightweight, file dapat dikelola terpisah

### Data Relationship
```
Users -> File Uploads -> Upload Sessions -> Players/Statistics
  |          |              |                    |
  |          |              |                    v
  |          |              |            Processed data in DB
  |          |              v
  |          |          Processing metadata
  |          v
  |      File metadata & paths
  v
User account & permissions
```

## Migrasi Data

### Dari Sistem Lama
1. Backup database dan files existing
2. Run `init_file_storage.py` untuk setup schema baru
3. Migrate existing files ke struktur user directory
4. Update database records dengan file paths baru

### Script Migrasi
```bash
# Initialize new database structure
python init_file_storage.py

# Start application with new system
python start_with_file_storage.bat
```

## Usage Examples

### Upload File Baru
1. User login ke sistem
2. Navigate ke Upload page
3. Select dan upload CSV file
4. File disimpan di `uploads/user_{id}/upload_{order}_{timestamp}.csv`
5. Database record dibuat di `file_uploads`
6. Data diproses dan disimpan di tables `players` dan `statistics`

### View Upload History
1. Navigate ke Upload History page
2. Lihat daftar semua upload dengan detail
3. Download atau delete file sesuai kebutuhan

### Admin Monitoring
1. Admin dapat melihat upload statistics semua user
2. Monitor storage usage
3. View recent uploads di Data Management page

## Konfigurasi

### File Storage Settings
```python
# app.py
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
```

### Cleanup Policy
```python
# Jumlah file yang disimpan per user
KEEP_LATEST_FILES = 10

# Auto cleanup setelah upload sukses
cleanup_old_uploads(user_id, keep_latest=KEEP_LATEST_FILES)
```

## Monitoring & Logging

### Activity Logging
- Semua upload, download, delete dicatat di `user_activity`
- IP address dan user agent tracking
- Timestamp untuk audit trail

### Storage Statistics
- Total storage per user
- File count per user
- System-wide storage usage
- File processing success rate

## Backup & Recovery

### File Backup Strategy
1. Regular backup direktori `uploads/`
2. Database backup dengan metadata file
3. Verify integrity file dan database records

### Disaster Recovery
1. Restore database dari backup
2. Restore file directories
3. Verify file paths dan accessibility
4. Re-run processing untuk file yang belum processed

## Troubleshooting

### Common Issues

**File Upload Gagal**
- Check file size (max 16MB)
- Check file extension (harus .csv)
- Check disk space
- Check user permissions

**File Tidak Dapat Didownload**
- Verify file exists di file system
- Check user access permissions
- Check file path di database

**Storage Full**
- Run cleanup script
- Increase cleanup retention
- Archive old files

### Debug Commands
```python
# Check user storage
python -c "
from app import get_user_uploads
uploads = get_user_uploads(user_id)
print(f'User {user_id} has {len(uploads)} files')
"

# Manual cleanup
python -c "
from app import cleanup_old_uploads
cleanup_old_uploads(user_id, keep_latest=5)
"
```

## Future Enhancements

### Planned Features
1. File compression untuk storage efficiency
2. Cloud storage integration (AWS S3, Google Cloud)
3. File versioning system
4. Bulk upload support
5. File sharing antar users (dengan permission)
6. Advanced search dan filtering
7. File preview functionality
8. Export/import user data

### Performance Optimizations
1. File caching strategy
2. Lazy loading untuk large file lists
3. Background processing untuk large uploads
4. CDN integration untuk file serving

## Kesimpulan

Implementasi user-specific file storage memberikan:

✅ **Organisasi yang lebih baik**: File terpisah per user dengan ordering  
✅ **Keamanan yang ditingkatkan**: Isolasi file dan access control  
✅ **Manajemen yang efisien**: History, download, delete, cleanup  
✅ **Skalabilitas**: Dapat menangani banyak user dan file  
✅ **Audit trail**: Logging lengkap untuk semua aktivitas file  
✅ **Database efisien**: Hanya metadata di database, file terpisah  

Sistem ini memberikan foundation yang solid untuk pengembangan fitur-fitur file management yang lebih advanced di masa depan.
