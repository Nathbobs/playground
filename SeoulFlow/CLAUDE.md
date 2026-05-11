# SeoulFlow — CLAUDE.md

## Project Overview
Real-time traffic monitoring system. YOLOv8-based vehicle detection + Kalman Filter 
tracking on video footage. FastAPI backend, Chrome extension sidebar frontend.

## Current Version
v1 — MP4 file input (no external API yet)
v2 (future) — ITS Korea live CCTV stream via openapi.its.go.kr

## Stack
- Backend: Python, FastAPI, uvicorn, OpenCV, Ultralytics YOLOv8, filterpy (Kalman)
- Frontend: Chrome Extension (Manifest V3), Vanilla JS, HTML, CSS
- Environment: Ubuntu, CUDA GPU, Docker

## Project Structure
seoulflow/
├── backend/
│   ├── main.py          # FastAPI app, endpoints
│   ├── pipeline.py      # Frame grabber + inference loop
│   ├── tracker.py       # Kalman Filter tracker
│   ├── scorer.py        # Congestion scoring logic
│   ├── models/          # YOLOv8 weights go here
│   └── videos/          # Test MP4 files go here
├── extension/
│   ├── manifest.json
│   ├── sidebar.html
│   ├── sidebar.js
│   └── sidebar.css
├── Dockerfile
├── requirements.txt
└── README.md

## Endpoints
- POST /start  → accepts { "video_path": "videos/test.mp4" }, starts pipeline
- GET /status  → returns current detection results as JSON
- GET /preview → MJPEG stream of annotated frames (debug use)
- POST /stop   → stops the pipeline

## /status Response Shape
{
  "total_vehicles": 12,
  "stationary": 7,
  "moving": 5,
  "congestion_score": 0.58,
  "status": "HEAVY",
  "fps": 12.4
}

## Congestion Levels
- FREE: 0–25% stationary
- LIGHT: 25–50%
- HEAVY: 50–75%
- GRIDLOCK: 75–100%

## Tracking
Use Kalman Filter (filterpy library) for vehicle tracking across frames.
Each track has an ID, position, velocity estimate, and stationary flag.
A vehicle is stationary if its velocity magnitude is below threshold (15px/frame) 
for 5 consecutive frames.

## Detection
- Model: YOLOv8n (nano, fastest)
- Classes: car (2), motorcycle (3), bus (5), truck (7) — COCO indices
- Confidence threshold: 0.4
- Run inference every other frame for performance

## CUDA
Always use CUDA if available:
  device = "cuda" if torch.cuda.is_available() else "cpu"
Never hardcode CPU.

## Chrome Extension
- Manifest V3
- Side panel (chrome.sidePanel API) not a popup
- Polls GET /status every 1000ms when monitoring is active
- Shows: total vehicles, stationary count, congestion status badge
- Status badge colors: green/yellow/orange/red for FREE/LIGHT/HEAVY/GRIDLOCK
- API base URL stored in a constant at top of sidebar.js for easy ngrok swap

## Style Rules
- Keep files small and single-responsibility
- No unnecessary dependencies
- All backend errors should return JSON, never crash the server
- Comments should explain WHY not WHAT

## Do Not
- Do not use React or any JS framework in the extension
- Do not use databases — keep state in memory
- Do not use threading where asyncio works
- Do not install packages not in requirements.txt without asking

## Environment Note
Code is scaffolded on macOS but executes on Ubuntu with CUDA.
Use Linux-compatible paths. No macOS-specific dependencies.