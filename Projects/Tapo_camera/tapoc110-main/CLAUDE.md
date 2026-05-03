# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time AprilTag-based camera calibration tool for Tapo C110 IP cameras. Single-file Python application (`test.py`) with threaded RTSP streaming and live accuracy verification.

## Running

```bash
python test.py
```

**Dependencies**: Python 3.10+, opencv-python, numpy, pupil-apriltags

## Architecture

**Single-file design** with two main classes:

- `FreshFrameReader`: Threaded RTSP reader with queue-based frame buffering for low-latency capture
- `TapoAprilTagTracker`: Main application - tag detection, calibration, UI, session management

**Key methods**:
- `_get_tag_object_points()`: Calculates 3D positions for tags based on grid layout
- `_draw_measurements()`: Real-time pose estimation and distance display on undistorted view
- `_verify_calibration()`: Console output of measured vs expected distances
- `recalibrate()`: OpenCV camera calibration with reprojection error calculation

## Configuration (top of test.py)

```python
# Camera connection
TAPO_USERNAME, TAPO_PASSWORD, IP_ADDRESS

# Tag grid (must match physical grid)
TAG_SIZE_MM = 32.0      # Tag outer edge size
GRID_COLS = 6           # Columns in grid
GRID_ROWS = 4           # Rows in grid
TAG_SPACING_MM = 48     # Center-to-center spacing
TAG_ID_START = 48       # First tag ID
```

## Key Files

- `test.py`: Main application
- `calibration.json`: Default calibration (auto-loaded on startup)
- `calibration_sessions/`: Session data and images

## Calibration Method

Uses OpenCV's `calibrateCamera()` with AprilTag corner detection:
1. User provides physical tag dimensions
2. 3D object points calculated from grid layout
3. 2D image points from AprilTag detector
4. Calibration finds camera matrix and distortion coefficients
5. Verification uses `solvePnP` to estimate tag poses and measure actual distances
