# Robotic Bricklaying — running-bond wall

Single-file demo of computed masonry: the robot picks bricks from a supply
point and lays a small wall in **running bond**, course by course. The wall
is generated from parameters (brick size, courses, joint gap) — edit them
and the same script builds a different wall. This is the canonical
architecture-robotics exercise (compare Gramazio Kohler's *programmed wall*).

## Run it

**Simulator first** (no hardware needed): open the
[web simulator](https://ineedabetterusrname.github.io/ur10e-simulator/) →
teach pendant → **Code** tab → paste `robotic_bricklaying.py` → **Run**.

**Real robot:** `pip install ur_rtde`, set `ROBOT_IP`, pendant in
*Remote Control*, speed slider low. The `time.sleep()` calls are
placeholders for your gripper I/O.

## Ideas to extend

- Replace the sleep placeholders with actual gripper commands
- Read brick positions from a Grasshopper-exported JSON instead of a grid
- Add a mortar/adhesive dispensing pass between courses
