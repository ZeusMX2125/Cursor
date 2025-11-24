# Quick Setup Guide

## Step 1: Add Your Credentials

Edit `backend/.env` and add your TopStepX credentials:

```
TOPSTEPX_USERNAME=your_username_here
TOPSTEPX_API_KEY=your_api_key_here
TOPSTEPX_BASE_URL=https://gateway.projectx.com/api
```

## Step 2: Start Backend Server

```powershell
cd backend
py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Step 3: Start Frontend (in new terminal)

```powershell
cd frontend
npm run dev
```

## Step 4: Access the Bot

Open your browser to: http://localhost:3000

## Troubleshooting

- If authentication fails, verify your credentials in `backend/.env`
- Check backend logs for detailed error messages
- Ensure ports 8000 (backend) and 3000 (frontend) are available

