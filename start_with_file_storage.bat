@echo off
echo ========================================
echo NBA MVP System with User File Storage
echo ========================================
echo.

echo Initializing database with file storage...
python init_file_storage.py

echo.
echo Starting Flask application...
echo.
echo Application will be available at: http://localhost:5000
echo.
echo Default accounts:
echo   Admin: admin / admin123
echo   Demo:  demo / demo123
echo.
echo Features:
echo   - User-specific file storage (uploads/user_X/)
echo   - Upload ordering and history tracking
echo   - Automatic file cleanup (keeps latest 10 per user)
echo   - Secure file validation and storage
echo.

python app.py

pause
