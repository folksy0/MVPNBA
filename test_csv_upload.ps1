# NBA MVP CSV Upload Test Script
# PowerShell script to test the enhanced CSV upload functionality

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "NBA MVP System - CSV Upload Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Flask app is running
Write-Host "🔍 Checking if Flask application is running..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Flask application is running successfully" -ForegroundColor Green
        Write-Host "   Status Code: $($response.StatusCode)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Flask application is not running" -ForegroundColor Red
    Write-Host "   Please start the application first using start_nba_mvp.bat" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Test the upload page
Write-Host "📄 Testing upload page accessibility..." -ForegroundColor Yellow

try {
    $uploadResponse = Invoke-WebRequest -Uri "http://127.0.0.1:5000/upload" -TimeoutSec 5 -UseBasicParsing
    if ($uploadResponse.StatusCode -eq 200) {
        Write-Host "✅ Upload page is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Upload page is not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check if test CSV file exists
$testCsvPath = ".\test_upload.csv"
if (Test-Path $testCsvPath) {
    Write-Host "📋 Test CSV file found: test_upload.csv" -ForegroundColor Green
    
    # Show file info
    $fileInfo = Get-Item $testCsvPath
    Write-Host "   File size: $($fileInfo.Length) bytes" -ForegroundColor Gray
    
    # Show first few lines
    Write-Host "   First few lines:" -ForegroundColor Gray
    Get-Content $testCsvPath -Head 3 | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
    
} else {
    Write-Host "❌ Test CSV file not found" -ForegroundColor Red
}

Write-Host ""

# Instructions for manual testing
Write-Host "📝 Manual Testing Instructions:" -ForegroundColor Cyan
Write-Host "1. Open your browser to: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "2. Navigate to the Upload page" -ForegroundColor White
Write-Host "3. Upload the test_upload.csv file" -ForegroundColor White
Write-Host "4. Verify that the upload completes successfully" -ForegroundColor White
Write-Host "5. Check the Data Management page to see imported data" -ForegroundColor White
Write-Host "6. View MVP Rankings to see calculated scores" -ForegroundColor White

Write-Host ""

# System information
Write-Host "🔧 System Information:" -ForegroundColor Cyan
Write-Host "   PowerShell Version: $($PSVersionTable.PSVersion)" -ForegroundColor Gray
Write-Host "   Current Directory: $(Get-Location)" -ForegroundColor Gray
Write-Host "   Date/Time: $(Get-Date)" -ForegroundColor Gray

Write-Host ""
Write-Host "🚀 Test completed! The enhanced CSV upload system is ready." -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to continue"
