# Paperless Parts API Integration Test Script
# This script tests the API integration after security improvements

Write-Host "=== Paperless Parts API Integration Testing ===" -ForegroundColor Cyan

# Get API token from environment variable
$apiToken = $env:PAPERLESS_API_TOKEN

# If API token is not set in environment, prompt for it
if (-not $apiToken) {
    $apiToken = Read-Host -Prompt "Enter your Paperless Parts API token"
}

# Base URL for Paperless Parts API
$apiBaseUrl = $env:API_BASE_URL
if (-not $apiBaseUrl) {
    $apiBaseUrl = "https://api.paperlessparts.com"
    Write-Host "API base URL not found in environment, using default: $apiBaseUrl" -ForegroundColor Yellow
}

# 1. Test API Connection
Write-Host "`n1. Testing API Connection..." -ForegroundColor Green

try {
    $headers = @{
        "Authorization" = "Token $apiToken"
        "Accept" = "application/json"
    }
    
    # Test endpoint - get company info (should be accessible with any valid token)
    $endpoint = "$apiBaseUrl/api/companies"
    
    Write-Host "Requesting: $endpoint"
    $response = Invoke-RestMethod -Uri $endpoint -Method Get -Headers $headers -ErrorAction Stop
    
    Write-Host "✅ API connection successful!" -ForegroundColor Green
    Write-Host "Response contains information about $($response.Count) companies"
    
    # Display some basic info about the first company
    if ($response.Count -gt 0) {
        $company = $response[0]
        Write-Host "Company details:"
        Write-Host "  Name: $($company.name)"
        Write-Host "  ID: $($company.id)"
    }
} catch {
    Write-Host "❌ API connection failed!" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "Status code: $statusCode"
        
        if ($statusCode -eq 401) {
            Write-Host "Authentication failed. Please check your API token." -ForegroundColor Red
        } elseif ($statusCode -eq 403) {
            Write-Host "Permission denied. Your API token may not have sufficient permissions." -ForegroundColor Red
        } else {
            Write-Host "Response: $($_.Exception.Response.StatusDescription)"
        }
    }
    
    Write-Host "Error: $($_.Exception.Message)"
}

# 2. Test Quotes API
Write-Host "`n2. Testing Quotes API..." -ForegroundColor Green

try {
    # Get recent quotes
    $quotesEndpoint = "$apiBaseUrl/api/quotes?limit=5"
    
    Write-Host "Requesting: $quotesEndpoint"
    $quotesResponse = Invoke-RestMethod -Uri $quotesEndpoint -Method Get -Headers $headers -ErrorAction Stop
    
    Write-Host "✅ Quotes API request successful!" -ForegroundColor Green
    Write-Host "Response contains information about $($quotesResponse.results.Count) quotes"
    
    # Display some basic info about the quotes
    if ($quotesResponse.results.Count -gt 0) {
        Write-Host "Recent quotes:"
        foreach ($quote in $quotesResponse.results) {
            Write-Host "  Quote Number: $($quote.quote_number), Status: $($quote.status)"
        }
    } else {
        Write-Host "No quotes found in the response."
    }
} catch {
    Write-Host "❌ Quotes API request failed!" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        Write-Host "Status code: $($_.Exception.Response.StatusCode.value__)"
        Write-Host "Response: $($_.Exception.Response.StatusDescription)"
    }
    
    Write-Host "Error: $($_.Exception.Message)"
}

# 3. Test Orders API
Write-Host "`n3. Testing Orders API..." -ForegroundColor Green

try {
    # Get recent orders
    $ordersEndpoint = "$apiBaseUrl/api/orders?limit=5"
    
    Write-Host "Requesting: $ordersEndpoint"
    $ordersResponse = Invoke-RestMethod -Uri $ordersEndpoint -Method Get -Headers $headers -ErrorAction Stop
    
    Write-Host "✅ Orders API request successful!" -ForegroundColor Green
    Write-Host "Response contains information about $($ordersResponse.results.Count) orders"
    
    # Display some basic info about the orders
    if ($ordersResponse.results.Count -gt 0) {
        Write-Host "Recent orders:"
        foreach ($order in $ordersResponse.results) {
            Write-Host "  Order Number: $($order.order_number), Status: $($order.status)"
        }
    } else {
        Write-Host "No orders found in the response."
    }
} catch {
    Write-Host "❌ Orders API request failed!" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        Write-Host "Status code: $($_.Exception.Response.StatusCode.value__)"
        Write-Host "Response: $($_.Exception.Response.StatusDescription)"
    }
    
    Write-Host "Error: $($_.Exception.Message)"
}

# 4. Webhook End-to-End Test Instructions
Write-Host "`n4. Webhook End-to-End Testing Instructions:" -ForegroundColor Green
Write-Host "   To perform a complete end-to-end test, follow these steps:" -ForegroundColor Yellow
Write-Host "   1. Start the webhook server: python -m scripts.app"
Write-Host "   2. Trigger a quote status change in Paperless Parts"
Write-Host "   3. Check the server logs to verify the webhook was received"
Write-Host "   4. Verify the CSV file was updated and uploaded to S3"
Write-Host "   Note: This requires manual intervention in the Paperless Parts UI"

Write-Host "`n=== Paperless Parts API Integration Testing Complete ===" -ForegroundColor Cyan