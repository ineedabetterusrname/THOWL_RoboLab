# Contour Crafting — layered printing toolpath

Single-file demo of additive construction: the TCP traces a **superellipse
profile layer by layer** — taper, twist, layer height and squareness are all
parameters — exactly the motion pattern of clay/concrete extrusion printing.
Swap the nozzle for a pen and it draws the layers on paper.

## Run it

**Simulator first** (no hardware needed): open the
[web simulator](https://ineedabetterusrname.github.io/ur10e-simulator/) →
teach pendant → **Code** tab → paste `contour_crafting.py` → **Run**.

**Real robot:** `pip install ur_rtde`, set `ROBOT_IP`, pendant in
*Remote Control*, speed slider low.

## Ideas to extend

- Drive an extruder/airbrush via the tool digital output at layer starts
- Generate the profile from a Grasshopper curve export instead of math
- Add a dwell + z-hop between layers for real material settling
