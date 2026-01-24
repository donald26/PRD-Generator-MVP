# 🚀 Quick Start Guide

## Step 1: Install Dependencies (One-time setup)

```bash
# Make sure you're in the project root
cd /Users/donald.fernandes/Documents/MyDocuments/Repos/PRD-Generator-MVP

# Activate your existing virtual environment (create if doesn't exist)
python3 -m venv .venv
source .venv/bin/activate

# Install ALL dependencies (existing prdgen + web app)
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart aiofiles

# Verify installation
python3 -c "import fastapi; import torch; print('✅ All dependencies installed!')"
```

## Step 2: Start the Backend Server

```bash
# From project root
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

✅ Backend is running!

## Step 3: Open the Web Interface

**Option A: Double-click**
- Open Finder
- Navigate to `frontend/` folder
- Double-click `index.html`

**Option B: Command line**
```bash
# In a NEW terminal window
open frontend/index.html
```

## Step 4: Test It!

### Test with Upload:
1. Click "Upload Documents" tab
2. Select some files from `examples/loan_underwriting_docs/`
3. Click "Generate PRD Artifacts"
4. Wait ~1-2 minutes
5. Download the ZIP file!

### Test with Folder Path:
1. Click "Use Folder Path" tab
2. Enter: `examples/loan_underwriting_docs`
3. Click "Generate PRD Artifacts"
4. See the output path where files are saved

## 🎉 That's It!

Your web app is now running!

- **Frontend:** http://localhost:8000 (via file:// protocol)
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Troubleshooting

### "Module not found" error
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Check Python path includes parent directory
echo $PYTHONPATH
```

### Backend won't start
```bash
# Check if port is already in use
lsof -i :8000

# Use a different port if needed
uvicorn app.main:app --port 8001
```

### Can't see uploaded files
```bash
# Check the temp directory
ls -la backend/temp/

# Check the outputs directory
ls -la backend/outputs/
```

## What's Next?

1. **Customize the UI** - Edit `frontend/index.html`
2. **Add features** - Modify `backend/app/main.py`
3. **Deploy to cloud** - Use Railway, Render, or Vercel
4. **Add authentication** - Implement user login (future)
5. **Add database** - Store projects and history (future)

---

**Need help?** Check `README_WEB_APP.md` for detailed documentation.
