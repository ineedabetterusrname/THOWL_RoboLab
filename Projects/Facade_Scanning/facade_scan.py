# ============================================================
# FACADE SCANNING - raster survey of a vertical surface
# ------------------------------------------------------------
# Building inspection pattern: the robot sweeps a wrist-mounted
# sensor (camera, thermal imager, ultrasonic probe...) across a
# vertical facade panel in a boustrophedon (serpentine) raster,
# pausing at each grid point to "capture". The same pattern is
# used for photogrammetry, NDT testing and paint/plaster QA.
#
# Runs unchanged on the lab UR10e and in the web simulator
# (teach pendant -> Code tab):
#   https://ineedabetterusrname.github.io/ur10e-simulator/
#
# Prerequisite (real robot): pip install ur_rtde
# ============================================================
import rtde_control
import rtde_receive
import time

ROBOT_IP = "YOUR_ROBOT_IP"     # ignored by the simulator

# ---- scan parameters ---------------------------------------
PANEL_W = 0.36                 # panel width  (along Y) [m]
PANEL_H = 0.24                 # panel height (along Z) [m]
COLS = 4                       # capture points per row
ROWS = 4                       # rows (top to bottom)
DWELL = 0.3                    # capture pause per point [s]

# ---- motion parameters -------------------------------------
SCAN_SPEED = 0.2               # travel speed between points [m/s]
WORK_POSE = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    rtde_c.moveJ(WORK_POSE, speed=1.0)
    base = rtde_r.getActualTCPPose()

    # panel frame: centred on the work pose, top row 5 cm below it.
    # The sensor keeps the work-pose orientation = constant standoff.
    y0 = base[1] - PANEL_W / 2
    z0 = base[2] - 0.05

    # A single row or column is a valid scan (a vertical or horizontal
    # line) - guard the division instead of crashing on COLS=1 / ROWS=1.
    y_step = PANEL_W / (COLS - 1) if COLS > 1 else 0.0
    z_step = PANEL_H / (ROWS - 1) if ROWS > 1 else 0.0

    captures = 0
    for row in range(ROWS):
        cols = range(COLS) if row % 2 == 0 else range(COLS - 1, -1, -1)
        for col in cols:                       # serpentine: no wasted travel
            pose = list(base)
            pose[1] = y0 + col * y_step
            pose[2] = z0 - row * z_step
            rtde_c.moveL(pose, speed=SCAN_SPEED)
            captures += 1
            print(f"capture {captures:02d}/{ROWS * COLS}  "
                  f"row {row + 1} col {col + 1}  y={pose[1]:.3f} z={pose[2]:.3f}")
            time.sleep(DWELL)                  # camera trigger placeholder

    rtde_c.moveJ(WORK_POSE, speed=1.0)
    print(f"scan complete: {captures} capture points over "
          f"{PANEL_W * 100:.0f} x {PANEL_H * 100:.0f} cm")
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
