# ============================================================
# CONTOUR CRAFTING - layered "printing" toolpath
# ------------------------------------------------------------
# Construction-scale 3D printing in miniature: the robot traces
# a closed profile layer by layer, exactly like a clay/concrete
# extrusion nozzle would. The profile is a superellipse whose
# radius is modulated per layer, so the "print" tapers and
# twists - all geometry is computed from the parameters below.
#
# Runs unchanged on the lab UR10e and in the web simulator
# (teach pendant -> Code tab):
#   https://ineedabetterusrname.github.io/ur10e-simulator/
#
# Prerequisite (real robot): pip install ur_rtde
# ============================================================
import rtde_control
import rtde_receive
import math

ROBOT_IP = "YOUR_ROBOT_IP"     # ignored by the simulator

# ---- print parameters --------------------------------------
LAYERS = 5                     # number of layers
LAYER_H = 0.02                 # layer height [m] (exaggerated to be visible)
SEGMENTS = 28                  # straight segments per layer
RADIUS = 0.09                  # base profile radius [m]
TAPER = 0.85                   # top-layer radius as a fraction of the base
TWIST = math.radians(18)       # total twist over the full height
SQUARENESS = 3.0               # superellipse exponent (2=circle, higher=squarer)

# ---- motion parameters -------------------------------------
PRINT_SPEED = 0.15             # nozzle travel speed [m/s]
WORK_POSE = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]

def profile_point(cx, cy, r, angle):
    """Superellipse point: |cos|^p, |sin|^p keep corners soft but square-ish."""
    p = 2.0 / SQUARENESS
    c, s = math.cos(angle), math.sin(angle)
    return (cx + r * math.copysign(abs(c) ** p, c),
            cy + r * math.copysign(abs(s) ** p, s))

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    rtde_c.moveJ(WORK_POSE, speed=1.0)
    base = rtde_r.getActualTCPPose()

    # print bed: centred on the work pose, 25 cm below it
    cx, cy, z0 = base[0], base[1], base[2] - 0.25

    for layer in range(LAYERS):
        t = layer / max(1, LAYERS - 1)
        r = RADIUS * (1 - t * (1 - TAPER))          # taper towards the top
        twist = TWIST * t                            # accumulated twist
        z = z0 + layer * LAYER_H
        print(f"layer {layer + 1}/{LAYERS}  r={r * 1000:.0f} mm")

        for k in range(SEGMENTS + 1):
            a = twist + 2 * math.pi * k / SEGMENTS
            x, y = profile_point(cx, cy, r, a)
            pose = list(base)
            pose[0], pose[1], pose[2] = x, y, z
            # first point of a layer: travel move; rest: "extrusion" moves
            rtde_c.moveL(pose, speed=PRINT_SPEED if k else 0.25)

    # lift the nozzle clear and go home
    end = rtde_r.getActualTCPPose()
    end[2] += 0.10
    rtde_c.moveL(end, speed=0.25)
    rtde_c.moveJ(WORK_POSE, speed=1.0)
    print("print finished:", LAYERS, "layers,", LAYERS * SEGMENTS, "extrusion segments")
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
