# Webhook Authentication Test Script
# This script tests the webhook authentication mechanisms after security improvements

# Configuration
$webhookUrl = "http://localhost:5000/webhook"
$webhookSecret = $env:WEBHOOK_SECRET  # Read from environment variable

# If webhook secret is not set in environment, prompt for it
if (-not $webhookSecret) {
    $webhookSecret = Read-Host -Prompt "Enter your webhook secret"
}

Write-Host "=== Webhook Authentication Testing ===" -ForegroundColor Cyan

# Test payload
$payload = @{
    type = "quote.status_changed"
    data = @{
        quote_number = "TEST-001"
        revision_number = "1"
        status = "Sent"
    }
} | ConvertTo-Json -Compress

Write-Host "`nTest payload:" -ForegroundColor Yellow
Write-Host $payload

# 1. Test Header-Based Authentication
Write-Host "`n1. Testing Header-Based Authentication..." -ForegroundColor Green

# Calculate HMAC signature
$hmacsha = New-Object System.Security.Cryptography.HMACSHA256
$hmacsha.Key = [System.Text.Encoding]::UTF8.GetBytes($webhookSecret)
$signature = [BitConverter]::ToString($hmacsha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))).Replace("-", "").ToLower()

Write-Host "Calculated signature: $signature"

try {
    $headers = @{
        "Content-Type" = "application/json"
        "X-Webhook-Signature" = $signature
    }
    
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $payload -Headers $headers -ErrorAction Stop
    Write-Host "✅ Header-based authentication successful!" -ForegroundColor Green
    Write-Host "Response: $response"
} catch {
    Write-Host "❌ Header-based authentication failed!" -ForegroundColor Red
    Write-Host "Status code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Response: $($_.Exception.Response.StatusDescription)"
    Write-Host "Error: $($_.Exception.Message)"
}

# 2. Test Token Parameter Authentication
Write-Host "`n2. Testing Token Parameter Authentication..." -ForegroundColor Green

try {
    $tokenUrl = "$webhookUrl`?token=$webhookSecret"
    $response = Invoke-RestMethod -Uri $tokenUrl -Method Post -Body $payload -Headers @{"Content-Type" = "application/json"} -ErrorAction Stop
    Write-Host "✅ Token parameter authentication successful!" -ForegroundColor Green
    Write-Host "Response: $response"
} catch {
    Write-Host "❌ Token parameter authentication failed!" -ForegroundColor Red
    Write-Host "Status code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Response: $($_.Exception.Response.StatusDescription)"
    Write-Host "Error: $($_.Exception.Message)"
}

# 3. Test Invalid Authentication
Write-Host "`n3. Testing Invalid Authentication (should fail)..." -ForegroundColor Green

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $payload -Headers @{"Content-Type" = "application/json"} -ErrorAction Stop
    Write-Host "❌ Test failed! Request with no authentication was accepted." -ForegroundColor Red
    Write-Host "Response: $response"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "✅ Authentication correctly rejected unauthorized request!" -ForegroundColor Green
        Write-Host "Status code: 401 (Expected)"
    } else {
        Write-Host "❓ Request failed but with unexpected status code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
        Write-Host "Response: $($_.Exception.Response.StatusDescription)"
        Write-Host "Error: $($_.Exception.Message)"
    }
}

Write-Host "`n=== Webhook Authentication Testing Complete ===" -ForegroundColor Cyan