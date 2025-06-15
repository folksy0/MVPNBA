@echo off
echo NBA MVP Decision Support System - Security Setup
echo ================================================

echo Installing security packages...
pip install bleach==6.1.0 MarkupSafe==2.1.3 requests==2.31.0

echo.
echo Security setup complete!
echo.
echo Security features enabled:
echo - XSS protection with HTML sanitization
echo - SQL injection prevention with parameterized queries
echo - File upload validation and sanitization
echo - Security headers (CSP, X-Frame-Options, etc.)
echo - Input validation and rate limiting
echo - Session security improvements
echo.

echo To test security, run:
echo   python security_test.py
echo.

echo To start the secure application:
echo   python start_nba_mvp.py
echo.

pause
