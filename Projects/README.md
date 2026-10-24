# Projects

Student and demo projects for the TH OWL Robo Lab UR10e. Each folder is
self-contained; open its own README for details.

| Folder | What it is | Run with |
|---|---|---|
| `Contour_Crafting/` | Layer-by-layer "3D printing" toolpath | `python contour_crafting.py` |
| `Facade_Scanning/` | Serpentine raster scan of a vertical panel | `python facade_scan.py` |
| `Robotic_Bricklaying/` | Pick-and-place running-bond wall | `python robotic_bricklaying.py` |
| `Interactive_robot/` | Hand-gesture teleoperation (webcam + MediaPipe), PyBullet sim, VR | `python scripts/main_sim.py` |
| `Tapo_Camera_Access/` | Lab camera access library and viewers | see its README |
| `Tapo_camera/tapoc110-main/` | AprilTag lens calibration for the Tapo C110 | `python test.py` |
| `Raspberrypi+AI_camera/` | Notes on pairing a Pi AI camera with the UR10e | read the `.md` |
| `Robo_lab_Model/`, `Hanger/` | Rhino / Grasshopper models | open in Rhino 8 |

## Before you run anything on the real robot

1. Start the robot on the pendant: see **Safety & Hardware → Starting the UR10e**
   on the lab website.
2. Switch the pendant to **Remote** control.
3. Try your script in the [web simulator](https://ineedabetterusrname.github.io/ur10e-simulator/)
   or `main_sim.py` first.
4. Keep the speed slider low and a hand near the E-Stop for the first run.
5. Stop a script with **Ctrl-C** (or ESC in the camera windows): the scripts
   stop the arm on exit.

## Never commit addresses or passwords

Scripts contain `ROBOT_IP = "YOUR_ROBOT_IP"` as a placeholder. Edit it
locally, but **do not commit** the real robot IP, camera addresses, camera
passwords or Wi-Fi details. Camera credentials are read from environment
variables or from a local `.env` file instead of the source.

`Tapo_Camera_Access/.env` is tracked as an empty template. After filling it
in, stop git from picking up your changes:

```bash
git update-index --skip-worktree Projects/Tapo_Camera_Access/.env
```

Before you push, check what you are about to commit:

```bash
git diff --cached | grep -nE "[0-9]{1,3}(\.[0-9]{1,3}){3}|PASS|password"
```
