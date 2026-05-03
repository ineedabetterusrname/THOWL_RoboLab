# Tapo C110 AprilTag Calibration Tool

A real-time camera calibration tool using AprilTag grids with live accuracy verification.

## Features

- **Multi-tag grid calibration**: Captures all visible AprilTags in a single frame
- **Real-time accuracy display**: Shows measured distances between tags with color-coded errors
- **Session management**: Save, load, and continue calibration sessions
- **Live undistortion preview**: See the corrected image in real-time
- **Pose-based verification**: Validates calibration by measuring actual 3D tag distances

## Requirements

- Python 3.10+
- OpenCV (`opencv-python`)
- NumPy
- pupil-apriltags

```bash
pip install opencv-python numpy pupil-apriltags
```

## Hardware Setup

1. **Camera**: TP-Link Tapo C110
2. **Camera Account**: Create credentials in Tapo App under `Camera Settings > Advanced Settings > Camera Account`
3. **AprilTag Grid**: Print a grid of `tag36h11` family tags with known size and spacing

## Configuration

Edit the settings at the top of `test.py`:

```python
# Camera connection
TAPO_USERNAME = "your_username"
TAPO_PASSWORD = "your_password"
IP_ADDRESS = "192.168.x.x"

# Tag grid settings (must match your printed grid)
TAG_SIZE_MM = 32.0      # Outer edge of tag in mm
GRID_COLS = 6           # Number of columns
GRID_ROWS = 4           # Number of rows
TAG_SPACING_MM = 48     # Center-to-center distance in mm
TAG_ID_START = 48       # First tag ID in grid
```

## Usage

```bash
python test.py
```

### Controls

| Key | Action |
|-----|--------|
| `c` | Capture calibration sample |
| `Enter` | Run calibration |
| `d` | Save calibration as default |
| `v` | Verify calibration accuracy |
| `l` | Load previous session |
| `b` | Rebuild old sessions from images |
| `r` | Reset current session |
| `s` | Save snapshot |
| `q` | Quit |

### Workflow

1. **Capture samples**: Show tag grid to camera, press `c` at various angles
2. **Check coverage**: Green overlay shows which frame regions have samples
3. **Calibrate**: Press `Enter` when you have enough samples (3+ minimum)
4. **Verify**: Check the undistorted view - measured distances should be close to expected
5. **Save**: Press `d` to save as default calibration

## Output

- `calibration.json`: Default calibration file (auto-loaded on startup)
- `calibration_sessions/`: Session folders containing:
  - `sample_X_raw.jpg`: Original captured frames
  - `sample_X_det.jpg`: Frames with detection overlay
  - `session_data.json`: Calibration data (for session continuation)
  - `calibration_result.json`: Final calibration parameters

## Accuracy Indicators

The undistorted view shows real-time distance measurements:
- **Green**: < 2% error (excellent)
- **Yellow**: 2-5% error (acceptable)
- **Red**: > 5% error (recalibrate needed)

## License

MIT
