# Python Samples — UR10e

Three single-file `ur_rtde` scripts, ordered by difficulty. Each runs
**unchanged** on the lab's UR10e *and* in the
[web simulator](https://ineedabetterusrname.github.io/ur10e-simulator/) —
open the simulator's teach pendant → **Code** tab, pick the sample from the
*Examples…* dropdown (or paste the file), and press **Run**.

| Sample | Teaches |
|---|---|
| `01_first_moves.py` | Connecting, reading joints/TCP, `moveJ` vs `moveL` |
| `02_pick_and_place.py` | The classic pick-and-place cycle, functions, approach heights |
| `03_draw_circle.py` | Cartesian toolpaths — generating `moveL` waypoints with math |

## Simulator first, robot second

Test in the simulator before booking robot time: it validates joint limits
and reachability, enforces real velocity/acceleration limits, and
protective-stops on self/floor collision — telling you exactly which command
tripped. If your script survives the simulator, the geometry is sound.

**On the real robot:** set `ROBOT_IP` (pendant → ☰ → About), switch the
pendant to *Remote Control*, keep the speed slider low and a hand near the
E-Stop for the first run.

Notes for the simulator: `print()` output appears in the built-in console;
camera/GUI libraries (`cv2`, `mediapipe`, …) don't exist in the browser —
keep samples pure `ur_rtde`.
