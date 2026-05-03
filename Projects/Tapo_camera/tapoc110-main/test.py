"""
Tapo C110 AprilTag Detection & Lens Correction (Low Latency)
==========================================================

Optimized for:
- Zero-latency RTSP streaming (Threaded Reader).
- Multi-tag calibration (Captures all visible tags).
- Non-blocking calculations with Visual Progress Bar.
"""

import cv2
import numpy as np
import threading
import queue
import time
import os
import json
from datetime import datetime
from pupil_apriltags import Detector

# ==========================================================
# CONFIGURATION
# ==========================================================
TAPO_USERNAME = "your_username"
TAPO_PASSWORD = "your_password"
IP_ADDRESS    = "192.168.x.x"

RTSP_URL = f"rtsp://{TAPO_USERNAME}:{TAPO_PASSWORD}@{IP_ADDRESS}:554/stream2"

# PRE-CALCULATED LENS PARAMETERS (used if calibration.json doesn't exist)
DEFAULT_CAMERA_MATRIX = np.array([
    [763.66362666, 0.0, 614.15437596],
    [0.0, 820.29669293, 342.7250384],
    [0.0, 0.0, 1.0]
], dtype=np.float32)

DEFAULT_DIST_COEFFS = np.array([
    [-0.2389019, -0.01560768, -0.01806229, -0.00104809, 0.04438377]
], dtype=np.float32)

def load_calibration():
    """Load calibration from calibration.json if it exists, otherwise use defaults."""
    if os.path.exists("calibration.json"):
        try:
            with open("calibration.json", 'r') as f:
                data = json.load(f)
            mtx = np.array(data["camera_matrix"], dtype=np.float32)
            dist = np.array(data["dist_coeffs"], dtype=np.float32)
            print(f"Loaded calibration from calibration.json")
            return mtx, dist
        except Exception as e:
            print(f"Error loading calibration.json: {e}")
    return DEFAULT_CAMERA_MATRIX, DEFAULT_DIST_COEFFS

CAMERA_MATRIX, DIST_COEFFS = load_calibration()

# Calibration settings
TAG_SIZE_MM = 32.0  # Physical size of AprilTag in millimeters (measure your tag!)
MIN_CALIBRATION_SAMPLES = 3  # Minimum samples for good calibration

# Grid layout settings (for multi-tag calibration)
GRID_COLS = 6        # Number of columns in tag grid
GRID_ROWS = 4        # Number of rows in tag grid
TAG_SPACING_MM = 48  # Distance between tag centers in mm
TAG_ID_START = 48    # First tag ID in the grid (bottom-left or top-left)

class FreshFrameReader:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.q = queue.Queue()
        self.stopped = False
        self.thread = threading.Thread(target=self._reader)
        self.thread.daemon = True
        self.thread.start()

    def _reader(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret: break
            if not self.q.empty():
                try: self.q.get_nowait()
                except queue.Empty: pass
            self.q.put(frame)
        self.cap.release()

    def read(self):
        return True, self.q.get()

    def isOpened(self):
        return self.cap.isOpened()

    def stop(self):
        self.stopped = True

class TapoAprilTagTracker:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.detector = Detector(families='tag36h11', nthreads=1)
        
        # Calibration Parameters
        self.camera_matrix = CAMERA_MATRIX
        self.dist_coeffs = DIST_COEFFS
        self.is_calibrated = True
        
        # Session State
        self.session_folder = None
        self.obj_points = []
        self.img_points = []
        self.sample_count = 0
        self.is_calculating = False
        self.calc_start_time = 0
        self.frame_size = None

        # Coverage tracking - divide frame into 3x3 grid regions
        self.region_coverage = [[False]*3 for _ in range(3)]

        # Session selection state
        self.pending_session_select = None

        # Use actual physical tag size for accurate calibration
        self.tag_size = TAG_SIZE_MM

    def _get_tag_object_points(self, tag_id):
        """Get 3D object points for a tag based on its grid position."""
        # Convert absolute tag ID to grid-relative index
        grid_index = tag_id - TAG_ID_START
        if grid_index < 0 or grid_index >= GRID_COLS * GRID_ROWS:
            return None  # Tag ID outside expected grid

        row = grid_index // GRID_COLS
        col = grid_index % GRID_COLS

        # Calculate tag origin (top-left corner position in grid)
        # Using same coordinate system as original: X right, Y down
        x = col * TAG_SPACING_MM
        y = row * TAG_SPACING_MM

        # Corner order must match pupil-apriltags output:
        # [0]=bottom-left, [1]=bottom-right, [2]=top-right, [3]=top-left (counter-clockwise)
        # In our coords (Y increases down): bottom=+Y, top=0, left=0, right=+X
        return np.array([
            [x, y + self.tag_size, 0],                    # bottom-left
            [x + self.tag_size, y + self.tag_size, 0],    # bottom-right
            [x + self.tag_size, y, 0],                    # top-right
            [x, y, 0]                                     # top-left
        ], dtype=np.float32)

    def _start_new_session(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = f"calibration_sessions/session_{timestamp}"
        os.makedirs(self.session_folder, exist_ok=True)
        print(f"Created new session folder: {self.session_folder}")

    def _save_session_data(self):
        """Save current calibration samples to session folder."""
        if not self.session_folder or not self.obj_points:
            return
        data = {
            "obj_points": [pts.tolist() for pts in self.obj_points],
            "img_points": [pts.tolist() for pts in self.img_points],
            "sample_count": self.sample_count,
            "region_coverage": self.region_coverage
        }
        with open(os.path.join(self.session_folder, "session_data.json"), 'w') as f:
            json.dump(data, f)

    def _load_session(self, session_path):
        """Load calibration samples from an existing session."""
        data_file = os.path.join(session_path, "session_data.json")
        if not os.path.exists(data_file):
            print(f"No session data found in {session_path}")
            return False

        try:
            with open(data_file, 'r') as f:
                data = json.load(f)

            self.obj_points = [np.array(pts, dtype=np.float32) for pts in data["obj_points"]]
            self.img_points = [np.array(pts, dtype=np.float32) for pts in data["img_points"]]
            self.sample_count = data["sample_count"]
            self.region_coverage = data.get("region_coverage", [[False]*3 for _ in range(3)])
            self.session_folder = session_path

            print(f"Loaded session: {session_path}")
            print(f"  Samples: {len(self.obj_points)}, Coverage: {sum(sum(row) for row in self.region_coverage)}/9")
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False

    def _list_sessions(self):
        """List available sessions and let user choose one."""
        sessions_dir = "calibration_sessions"
        if not os.path.exists(sessions_dir):
            print("No calibration sessions found.")
            return None

        sessions = []
        for name in sorted(os.listdir(sessions_dir), reverse=True):  # Most recent first
            path = os.path.join(sessions_dir, name)
            if os.path.isdir(path):
                data_file = os.path.join(path, "session_data.json")
                result_file = os.path.join(path, "calibration_result.json")
                has_data = os.path.exists(data_file)
                has_result = os.path.exists(result_file)

                samples = 0
                if has_data:
                    try:
                        with open(data_file, 'r') as f:
                            data = json.load(f)
                        samples = len(data.get("obj_points", []))
                    except:
                        pass

                sessions.append((name, path, samples, has_data, has_result))

        if not sessions:
            print("No sessions found.")
            return None

        # Only show sessions that can be continued (have data)
        continuable = [(n, p, s, d, r) for n, p, s, d, r in sessions if d]

        print("\n=== Sessions (most recent first) ===")
        if continuable:
            print("Can continue:")
            for i, (name, path, samples, has_data, has_result) in enumerate(continuable[:9]):
                status = f"{samples} samples"
                if has_result:
                    status += ", calibrated"
                print(f"  {i+1}. {name} ({status})")
        else:
            print("  No sessions with saved data to continue.")
            print("  (Old sessions only have images, not calibration data)")
            print("  Start a new session with 'c' - it will be saved automatically.")

        print(f"  0. Cancel")
        print("====================================")

        return continuable if continuable else None

    def _rebuild_sessions(self):
        """Rebuild session data from saved images."""
        sessions_dir = "calibration_sessions"
        if not os.path.exists(sessions_dir):
            print("No calibration sessions found.")
            return

        rebuilt_count = 0
        for name in sorted(os.listdir(sessions_dir)):
            path = os.path.join(sessions_dir, name)
            if not os.path.isdir(path):
                continue

            data_file = os.path.join(path, "session_data.json")
            if os.path.exists(data_file):
                continue  # Already has data

            # Find raw images in this session
            raw_images = sorted([f for f in os.listdir(path) if f.endswith("_raw.jpg")])
            if not raw_images:
                continue

            print(f"Rebuilding {name} from {len(raw_images)} images...")

            obj_points = []
            img_points = []
            region_coverage = [[False]*3 for _ in range(3)]

            for img_file in raw_images:
                img_path = os.path.join(path, img_file)
                frame = cv2.imread(img_path)
                if frame is None:
                    continue

                h, w = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                tags = self.detector.detect(gray)

                frame_obj_points = []
                frame_img_points = []

                for tag in tags:
                    tag_obj_pts = self._get_tag_object_points(tag.tag_id)
                    if tag_obj_pts is not None:
                        frame_obj_points.append(tag_obj_pts)
                        frame_img_points.append(tag.corners.astype(np.float32))

                        # Track coverage
                        center = tag.corners.mean(axis=0)
                        region_x = min(2, int(center[0] / (w / 3)))
                        region_y = min(2, int(center[1] / (h / 3)))
                        region_coverage[region_y][region_x] = True

                if frame_obj_points:
                    obj_points.append(np.vstack(frame_obj_points))
                    img_points.append(np.vstack(frame_img_points))

            if obj_points:
                # Save rebuilt session data
                data = {
                    "obj_points": [pts.tolist() for pts in obj_points],
                    "img_points": [pts.tolist() for pts in img_points],
                    "sample_count": len(obj_points),
                    "region_coverage": region_coverage
                }
                with open(data_file, 'w') as f:
                    json.dump(data, f)
                print(f"  -> Rebuilt {len(obj_points)} samples")
                rebuilt_count += 1
            else:
                print(f"  -> No valid tags found in images")

        if rebuilt_count > 0:
            print(f"\nRebuilt {rebuilt_count} sessions. Press 'l' to load one.")
        else:
            print("No sessions could be rebuilt.")

    def run(self):
        reader = FreshFrameReader(self.rtsp_url)
        if not reader.isOpened():
            print("Error: Could not open stream.")
            return

        print("\n" + "="*50)
        print("  TAPO C110 APRILTAG CALIBRATION TOOL")
        print("="*50)
        print(f"  Grid: {GRID_COLS}x{GRID_ROWS} | Tags: {TAG_ID_START}-{TAG_ID_START + GRID_COLS * GRID_ROWS - 1}")
        print(f"  Tag size: {TAG_SIZE_MM}mm | Spacing: {TAG_SPACING_MM}mm")
        print("="*50 + "\n")

        while True:
            ret, frame = reader.read()
            if not ret: break

            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            tags = self.detector.detect(gray)

            display_frame = frame.copy()
            valid_tags = 0
            for tag in tags:
                corners = tag.corners.astype(np.int32)
                # Check if tag is in our expected grid
                grid_index = tag.tag_id - TAG_ID_START
                is_valid = 0 <= grid_index < GRID_COLS * GRID_ROWS
                color = (0, 255, 0) if is_valid else (0, 165, 255)  # Green for valid, orange for out-of-grid
                if is_valid:
                    valid_tags += 1

                for i in range(4):
                    cv2.line(display_frame, tuple(corners[i]), tuple(corners[(i+1)%4]), color, 2)
                # Draw tag ID with background for readability
                label = f"{tag.tag_id}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(display_frame, (corners[0][0]-2, corners[0][1]-th-12),
                              (corners[0][0]+tw+2, corners[0][1]-8), color, -1)
                cv2.putText(display_frame, label, (corners[0][0], corners[0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            # Draw UI Overlays
            if self.is_calculating:
                self._draw_progress_bar(display_frame, w, h)
            else:
                if self.is_calibrated:
                    # alpha=0 crops to valid pixels only, alpha=1 keeps all pixels with black borders
                    new_mtx, roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.dist_coeffs, (w, h), 0, (w, h))
                    undistorted = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs, None, new_mtx)
                    # Crop to the valid region
                    x_roi, y_roi, rw, rh = roi
                    if rw > 0 and rh > 0:
                        undistorted = undistorted[y_roi:y_roi+rh, x_roi:x_roi+rw]

                    # Draw real-time measurements on undistorted view
                    self._draw_measurements(undistorted, tags, new_mtx, roi)
                    cv2.imshow('Undistorted + Measurements', undistorted)

            # Draw coverage grid overlay
            self._draw_coverage_grid(display_frame, w, h)

            # Draw status panel
            self._draw_status_panel(display_frame, w, h, valid_tags)

            cv2.imshow('Tapo C110 - Control', display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite("snapshot.jpg", frame)
                print("Snapshot saved.")
            elif key == ord('c') and not self.is_calculating:
                if tags:
                    if self.session_folder is None: self._start_new_session()

                    # Collect all valid tags (those within expected grid IDs)
                    frame_obj_points = []
                    frame_img_points = []
                    captured_ids = []

                    for tag in tags:
                        obj_pts = self._get_tag_object_points(tag.tag_id)
                        if obj_pts is not None:
                            frame_obj_points.append(obj_pts)
                            frame_img_points.append(tag.corners.astype(np.float32))
                            captured_ids.append(tag.tag_id)

                            # Track coverage based on tag center
                            center = tag.corners.mean(axis=0)
                            region_x = min(2, int(center[0] / (w / 3)))
                            region_y = min(2, int(center[1] / (h / 3)))
                            self.region_coverage[region_y][region_x] = True

                    if frame_obj_points:
                        self.sample_count += 1
                        cv2.imwrite(os.path.join(self.session_folder, f"sample_{self.sample_count}_raw.jpg"), frame)
                        cv2.imwrite(os.path.join(self.session_folder, f"sample_{self.sample_count}_det.jpg"), display_frame)

                        # Store all tags from this frame as a single calibration view
                        self.obj_points.append(np.vstack(frame_obj_points))
                        self.img_points.append(np.vstack(frame_img_points))

                        # Save session data for later continuation
                        self._save_session_data()

                        covered = sum(sum(row) for row in self.region_coverage)
                        print(f"Sample {self.sample_count}: captured {len(captured_ids)} tags (IDs: {captured_ids}). Coverage: {covered}/9")
                    else:
                        print("No valid grid tags detected (check tag IDs match grid).")
                else:
                    print("No tags detected.")
            elif key == 13: # Enter
                if not self.is_calculating:
                    self.calc_start_time = time.time()
                    calc_thread = threading.Thread(target=self.recalibrate, args=(w, h))
                    calc_thread.start()
            elif key == ord('r') and not self.is_calculating:
                self.obj_points = []
                self.img_points = []
                self.sample_count = 0
                self.region_coverage = [[False]*3 for _ in range(3)]
                self.session_folder = None
                print("Calibration reset. Start new session with 'c'.")
            elif key == ord('d') and self.is_calibrated:
                # Save current calibration as default
                data = {
                    "camera_matrix": self.camera_matrix.tolist(),
                    "dist_coeffs": self.dist_coeffs.tolist()
                }
                with open("calibration.json", 'w') as f:
                    json.dump(data, f, indent=4)
                print("Saved current calibration to calibration.json")
            elif key == ord('v') and self.is_calibrated:
                self._verify_calibration(tags, gray.shape[1], gray.shape[0])
            elif key == ord('l') and not self.is_calculating:
                sessions = self._list_sessions()
                if sessions:
                    self.pending_session_select = sessions
            elif self.pending_session_select and ord('0') <= key <= ord('9'):
                idx = key - ord('0')
                if idx == 0:
                    print("Selection cancelled.")
                elif 1 <= idx <= len(self.pending_session_select):
                    _, path, _, _, _ = self.pending_session_select[idx - 1]
                    self._load_session(path)
                else:
                    print(f"Invalid selection: {idx}")
                self.pending_session_select = None
            elif key == ord('b') and not self.is_calculating:
                self._rebuild_sessions()

        reader.stop()
        cv2.destroyAllWindows()

    def _draw_progress_bar(self, img, w, h):
        # Background box
        bw, bh = 300, 60
        bx2, by2 = w // 2 + bw // 2, h // 2 + bh // 2
        bx1, by1 = w // 2 - bw // 2, h // 2 - bh // 2
        cv2.rectangle(img, (bx1, by1), (bx2, by2), (40, 40, 40), -1)
        cv2.rectangle(img, (bx1, by1), (bx2, by2), (200, 200, 200), 2)

        # "Calculating" Text
        cv2.putText(img, "CALCULATING LENS...", (bx1 + 10, by1 + 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Animated Progress Bar (Marquee style)
        bar_x1 = bx1 + 10
        bar_x2 = bx2 - 10
        bar_w = bar_x2 - bar_x1
        
        # Calculate moving block position based on time
        t = (time.time() - self.calc_start_time) * 2.0 # speed
        block_w = 60
        pos = (np.sin(t) + 1) / 2 # Oscillator 0 to 1
        x_shift = int(pos * (bar_w - block_w))
        
        # Track background
        cv2.rectangle(img, (bar_x1, by1 + 35), (bar_x2, by1 + 50), (100, 100, 100), -1)
        # Moving block
        cv2.rectangle(img, (bar_x1 + x_shift, by1 + 35), (bar_x1 + x_shift + block_w, by1 + 50), (0, 255, 0), -1)

    def _draw_measurements(self, img, tags, new_mtx, roi):
        """Draw real-time distance measurements between adjacent tags."""
        if not tags or len(tags) < 2:
            return

        x_roi, y_roi, rw, rh = roi
        if rw <= 0 or rh <= 0:
            return

        # Get 3D pose and 2D center for each tag
        tag_data = {}  # tag_id -> (3D_position, 2D_center_in_undistorted)

        half = self.tag_size / 2
        obj_points_local = np.array([
            [-half, -half, 0], [half, -half, 0],
            [half, half, 0], [-half, half, 0]
        ], dtype=np.float32)

        for tag in tags:
            grid_index = tag.tag_id - TAG_ID_START
            if grid_index < 0 or grid_index >= GRID_COLS * GRID_ROWS:
                continue

            img_points = tag.corners.astype(np.float32)

            # Estimate 3D pose
            success, rvec, tvec = cv2.solvePnP(
                obj_points_local, img_points,
                self.camera_matrix, self.dist_coeffs
            )
            if not success:
                continue

            # Undistort the tag center for display
            center_distorted = img_points.mean(axis=0).reshape(1, 1, 2)
            center_undistorted = cv2.undistortPoints(center_distorted, self.camera_matrix, self.dist_coeffs, P=new_mtx)
            cx, cy = center_undistorted[0, 0]

            # Adjust for ROI crop
            cx -= x_roi
            cy -= y_roi

            tag_data[tag.tag_id] = (tvec.flatten(), (int(cx), int(cy)))

        # Calculate distances between adjacent pairs
        measurements = []
        for tag_id, (pos3d, center2d) in tag_data.items():
            grid_index = tag_id - TAG_ID_START
            row = grid_index // GRID_COLS
            col = grid_index % GRID_COLS

            # Horizontal neighbor
            right_id = tag_id + 1
            if col < GRID_COLS - 1 and right_id in tag_data:
                pos3d_right, center2d_right = tag_data[right_id]
                dist = np.linalg.norm(pos3d_right - pos3d)
                measurements.append((center2d, center2d_right, dist))

            # Vertical neighbor
            below_id = tag_id + GRID_COLS
            if row < GRID_ROWS - 1 and below_id in tag_data:
                pos3d_below, center2d_below = tag_data[below_id]
                dist = np.linalg.norm(pos3d_below - pos3d)
                measurements.append((center2d, center2d_below, dist))

        # Draw measurements on image
        errors = []
        for (x1, y1), (x2, y2), dist in measurements:
            error = dist - TAG_SPACING_MM
            errors.append(abs(error))

            # Color based on error: green=good, yellow=ok, red=bad
            error_pct = abs(error) / TAG_SPACING_MM * 100
            if error_pct < 2:
                color = (0, 255, 0)  # Green
            elif error_pct < 5:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red

            # Draw line between tags
            cv2.line(img, (x1, y1), (x2, y2), color, 2)

            # Draw distance label at midpoint
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.putText(img, f"{dist:.1f}", (mx - 15, my - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Draw summary stats panel
        if errors:
            mean_err = np.mean(errors)
            max_err = np.max(errors)
            h_img, w_img = img.shape[:2]

            # Background panel
            panel_h = 70
            overlay = img.copy()
            cv2.rectangle(overlay, (0, h_img - panel_h), (220, h_img), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

            # Stats text
            cv2.putText(img, f"Expected: {TAG_SPACING_MM}mm", (10, h_img - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            # Color-code the error display
            err_color = (0, 255, 0) if mean_err < 1 else (0, 255, 255) if mean_err < 2 else (0, 0, 255)
            cv2.putText(img, f"Mean err: {mean_err:.2f}mm ({100*mean_err/TAG_SPACING_MM:.1f}%)", (10, h_img - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, err_color, 1)
            cv2.putText(img, f"Max err:  {max_err:.2f}mm ({100*max_err/TAG_SPACING_MM:.1f}%)", (10, h_img - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    def _draw_coverage_grid(self, img, w, h):
        """Draw 3x3 grid showing which regions have been sampled."""
        cell_w, cell_h = w // 3, h // 3
        for row in range(3):
            for col in range(3):
                x1, y1 = col * cell_w, row * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                if self.region_coverage[row][col]:
                    # Green overlay for covered regions
                    overlay = img.copy()
                    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
                    cv2.addWeighted(overlay, 0.1, img, 0.9, 0, img)
                # Draw grid lines
                cv2.rectangle(img, (x1, y1), (x2, y2), (80, 80, 80), 1)

    def _draw_status_panel(self, img, w, h, valid_tags):
        """Draw clean status panel with all info."""
        # Semi-transparent background for status area
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        # Session info
        session_name = os.path.basename(self.session_folder) if self.session_folder else "No session"
        covered = sum(sum(row) for row in self.region_coverage)

        # Line 1: Tags and samples
        line1 = f"Tags: {valid_tags}  |  Samples: {len(self.obj_points)}/{MIN_CALIBRATION_SAMPLES}  |  Coverage: {covered}/9"
        cv2.putText(img, line1, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Line 2: Session
        cv2.putText(img, f"Session: {session_name}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        # Ready indicator
        if len(self.obj_points) >= MIN_CALIBRATION_SAMPLES:
            cv2.putText(img, "READY - Press Enter to calibrate", (w - 300, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Session selection prompt
        if self.pending_session_select:
            cv2.rectangle(img, (w//4, h//2 - 20), (3*w//4, h//2 + 20), (0, 0, 0), -1)
            cv2.rectangle(img, (w//4, h//2 - 20), (3*w//4, h//2 + 20), (0, 255, 255), 2)
            cv2.putText(img, "Enter session number (see console)", (w//4 + 20, h//2 + 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Help hint at bottom
        cv2.putText(img, "c=Capture  Enter=Calibrate  d=Save  v=Verify  l=Load  r=Reset  q=Quit",
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    def _verify_calibration(self, tags, w, h):
        """Verify calibration by measuring actual tag distances vs expected."""
        if not tags or len(tags) < 2:
            print("Need at least 2 visible tags to verify.")
            return

        print("\n=== CALIBRATION VERIFICATION ===")

        # Get 3D pose for each detected tag
        tag_positions = {}  # tag_id -> 3D center position

        # Define tag corners in tag's local coordinate system (centered at origin)
        half = self.tag_size / 2
        obj_points_local = np.array([
            [-half, -half, 0],
            [half, -half, 0],
            [half, half, 0],
            [-half, half, 0]
        ], dtype=np.float32)

        for tag in tags:
            grid_index = tag.tag_id - TAG_ID_START
            if grid_index < 0 or grid_index >= GRID_COLS * GRID_ROWS:
                continue

            img_points = tag.corners.astype(np.float32)

            # Estimate pose using solvePnP
            success, rvec, tvec = cv2.solvePnP(
                obj_points_local, img_points,
                self.camera_matrix, self.dist_coeffs
            )

            if success:
                # tvec is the position of tag center in camera coordinates
                tag_positions[tag.tag_id] = tvec.flatten()

        if len(tag_positions) < 2:
            print("Could not estimate pose for enough tags.")
            return

        # Find adjacent tag pairs and measure distances
        horizontal_errors = []
        vertical_errors = []

        for tag_id, pos in tag_positions.items():
            grid_index = tag_id - TAG_ID_START
            row = grid_index // GRID_COLS
            col = grid_index % GRID_COLS

            # Check horizontal neighbor (same row, col+1)
            right_id = tag_id + 1
            if col < GRID_COLS - 1 and right_id in tag_positions:
                dist = np.linalg.norm(tag_positions[right_id] - pos)
                error = dist - TAG_SPACING_MM
                horizontal_errors.append((tag_id, right_id, dist, error))

            # Check vertical neighbor (row+1, same col)
            below_id = tag_id + GRID_COLS
            if row < GRID_ROWS - 1 and below_id in tag_positions:
                dist = np.linalg.norm(tag_positions[below_id] - pos)
                error = dist - TAG_SPACING_MM
                vertical_errors.append((tag_id, below_id, dist, error))

        # Report results
        all_errors = horizontal_errors + vertical_errors
        if not all_errors:
            print("No adjacent tag pairs found.")
            return

        print(f"Expected spacing: {TAG_SPACING_MM}mm")
        print(f"Measured {len(all_errors)} adjacent pairs:\n")

        measured_dists = [e[2] for e in all_errors]
        errors_mm = [abs(e[3]) for e in all_errors]

        print(f"  Measured distances: {np.min(measured_dists):.1f} - {np.max(measured_dists):.1f}mm")
        print(f"  Mean measured: {np.mean(measured_dists):.2f}mm")
        print(f"  Mean error: {np.mean(errors_mm):.2f}mm ({100*np.mean(errors_mm)/TAG_SPACING_MM:.1f}%)")
        print(f"  Max error: {np.max(errors_mm):.2f}mm ({100*np.max(errors_mm)/TAG_SPACING_MM:.1f}%)")

        # Show worst pairs
        all_errors.sort(key=lambda x: abs(x[3]), reverse=True)
        print(f"\nWorst pairs:")
        for tag1, tag2, dist, err in all_errors[:3]:
            print(f"  Tags {tag1}-{tag2}: {dist:.1f}mm (error: {err:+.1f}mm)")

        print("================================\n")

    def recalibrate(self, w, h):
        if len(self.obj_points) < MIN_CALIBRATION_SAMPLES:
            print(f"Need at least {MIN_CALIBRATION_SAMPLES} samples. Currently have {len(self.obj_points)}.")
            return

        covered = sum(sum(row) for row in self.region_coverage)
        if covered < 5:
            print(f"Warning: Only {covered}/9 frame regions covered. Move tag to more positions for better results.")

        self.is_calculating = True
        try:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                self.obj_points, self.img_points, (w, h), None, None
            )
            if ret:
                self.camera_matrix, self.dist_coeffs = mtx, dist
                self.is_calibrated = True

                # Calculate reprojection error
                total_error = 0
                total_points = 0
                for i in range(len(self.obj_points)):
                    img_points_proj, _ = cv2.projectPoints(
                        self.obj_points[i], rvecs[i], tvecs[i], mtx, dist
                    )
                    error = cv2.norm(self.img_points[i], img_points_proj.reshape(-1, 2), cv2.NORM_L2)
                    total_error += error ** 2
                    total_points += len(self.obj_points[i])
                mean_error = np.sqrt(total_error / total_points)

                if self.session_folder:
                    results = {
                        "camera_matrix": mtx.tolist(),
                        "dist_coeffs": dist.tolist(),
                        "reprojection_error_px": mean_error,
                        "num_samples": len(self.obj_points),
                        "total_points": total_points,
                        "tag_size_mm": self.tag_size,
                        "grid": {"cols": GRID_COLS, "rows": GRID_ROWS, "spacing_mm": TAG_SPACING_MM, "id_start": TAG_ID_START},
                        "image_size": [w, h]
                    }
                    with open(os.path.join(self.session_folder, "calibration_result.json"), 'w') as f:
                        json.dump(results, f, indent=4)

                print(f"Calibration successful! Reprojection error: {mean_error:.3f} px")
                if mean_error > 1.0:
                    print("Warning: Error > 1px. Consider more samples at varied angles.")
            else:
                print("Calibration failed - cv2.calibrateCamera returned False")
        except Exception as e:
            print(f"Calibration error: {e}")
        finally:
            self.is_calculating = False

if __name__ == "__main__":
    tracker = TapoAprilTagTracker(RTSP_URL)
    tracker.run()