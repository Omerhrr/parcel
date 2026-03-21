#!/bin/bash

echo "🚀 Starting ParcelFlow..."

# Start backend
echo "Starting Backend API on port 8000..."
cd backend
python -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -r requirements.txt -q
python run.py &
BACKEND_PID=$!

# Start frontend
echo "Starting Frontend on port 5000..."
cd ../frontend
python -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -r requirements.txt -q
python run.py &
FRONTEND_PID=$!

echo ""
echo "✅ ParcelFlow is running!"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/api/docs"
echo "   - Frontend: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
