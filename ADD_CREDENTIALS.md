# Add Your TopStepX Credentials

## Quick Method (Recommended)

Run this PowerShell script:
```powershell
.\setup_credentials.ps1
```

## Manual Method

Edit `backend/.env` and replace these lines:

```
TOPSTEPX_USERNAME=your_actual_username_here
TOPSTEPX_API_KEY=your_actual_api_key_here
```

**Important:** 
- Get your API key from: https://topstepx.com (ProjectX settings)
- Keep these credentials secure - never commit them to git

## After Adding Credentials

Run:
```powershell
.\START_BOT.ps1
```

This will start both backend and frontend servers automatically.

