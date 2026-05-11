# SeoulFlow

Real-time vehicle detection and traffic congestion monitoring.  
YOLOv8n + Kalman Filter tracking on MP4 footage, served via FastAPI, visualized in a Chrome extension sidebar.

## Quick Start (Docker)

```bash
# Build
docker build -t seoulflow .

# Run (GPU)
docker run --gpus all -p 8000:8000 -v $(pwd)/backend/videos:/app/backend/videos seoulflow

# Run (CPU fallback)
docker run -p 8000:8000 -v $(pwd)/backend/videos:/app/backend/videos seoulflow
```

## Quick Start (Local)

```bash
pip install -r requirements.txt
# also: pip install torch torchvision  (if not in a pytorch Docker image)

# Download YOLOv8n weights (auto-downloads on first run via ultralytics)
uvicorn backend.main:app --reload
```

## API

| Method | Path | Body / Notes |
|--------|------|--------------|
| POST | `/start` | `{"video_path": "videos/test.mp4"}` |
| GET | `/status` | Returns congestion JSON |
| GET | `/preview` | MJPEG stream of annotated frames |
| POST | `/stop` | Stops the pipeline |

### `/status` response

```json
{
  "total_vehicles": 12,
  "stationary": 7,
  "moving": 5,
  "congestion_score": 0.583,
  "status": "HEAVY",
  "fps": 12.4
}
```

## Congestion levels

| Level | Stationary ratio |
|-------|-----------------|
| FREE | 0–25% |
| LIGHT | 25–50% |
| HEAVY | 50–75% |
| GRIDLOCK | 75–100% |

## Chrome Extension

1. Open `chrome://extensions`, enable **Developer mode**
2. Click **Load unpacked** → select the `extension/` folder
3. Click the SeoulFlow toolbar icon to open the side panel
4. Enter the video path and click **Start**

> If the backend runs remotely (e.g. via ngrok), update `API_BASE` at the top of `extension/sidebar.js`.

## Project Layout

```
backend/
  main.py       FastAPI app + endpoints
  pipeline.py   Frame grab → YOLOv8 inference → tracker update loop
  tracker.py    Kalman Filter multi-object tracker (filterpy)
  scorer.py     Congestion score + level classification
  models/       Place yolov8n.pt here (auto-downloaded on first run)
  videos/       Place test .mp4 files here
extension/
  manifest.json  MV3 side panel extension
  sidebar.html/js/css
```
