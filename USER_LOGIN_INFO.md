NBA MVP Application - User Login Information
=============================================

BERDASARKAN ANALISIS DATABASE DAN KODE:

1. USER YANG TERSEDIA:
   - Username: admin
     Password: admin123
     Email: admin@nbamvp.com
     Role: admin (administrator)
   
   - Username: ikhlas
     Password: [tidak diketahui - perlu reset atau tanya user]
     Email: ikhlas@gmail.com
     Role: user
   
   - Username: demo
     Password: [tidak diketahui - perlu reset atau tanya user]
     Email: demo@nbamvp.com
     Role: user
   
   - Username: Ervin
     Password: [tidak diketahui - perlu reset atau tanya user]
     Email: ervin@gmail.com
     Role: user

2. CARA LOGIN:
   - Buka aplikasi di browser
   - Klik tombol Login
   - Masukkan username dan password
   - Untuk admin: username = "admin", password = "admin123"

3. DEFAULT ADMIN CREDENTIALS:
   Username: admin
   Password: admin123
   
   (Kredensial ini dibuat otomatis saat aplikasi pertama kali dijalankan)

4. SISTEM KEAMANAN:
   - Password disimpan dalam bentuk hash menggunakan scrypt
   - Session management untuk melacak user yang login
   - Role-based access (admin vs user)

5. CARA MENAMBAH USER BARU:
   - Login sebagai admin
   - Gunakan fitur registrasi atau admin panel
   - Atau jalankan script Python untuk menambah user

6. JIKA LUPA PASSWORD:
   - Untuk user lain selain admin, perlu reset password melalui database
   - Atau buat user baru

REKOMENDASI KEAMANAN:
- Ganti password default admin setelah pertama kali login
- Gunakan password yang kuat
- Backup database secara berkala

CATATAN TEKNIS:
- Database: SQLite (nba_mvp.db)
- Hash method: scrypt dengan parameter 32768:8:1
- Session timeout: sesuai konfigurasi Flask
