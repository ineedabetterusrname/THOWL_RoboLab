# ============================================================
# SAMPLE 3 - DRAW A CIRCLE
# Trace a horizontal circle with the TCP using short moveL
# segments - the basic recipe behind any toolpath (welding,
# gluing, drawing...). Try changing RADIUS or SEGMENTS.
# ============================================================
import rtde_control
import rtde_receive
import math

ROBOT_IP = "YOUR_ROBOT_IP"   # ignored by the simulator

RADIUS = 0.10        # circle radius [m]
SEGMENTS = 24        # straight segments approximating the circle

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    work = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]
    rtde_c.moveJ(work, speed=1.0)

    # circle centre = current TCP; keep Z and orientation fixed
    cx, cy = rtde_r.getActualTCPPose()[:2]
    pose = rtde_r.getActualTCPPose()

    def waypoint(k):
        a = 2 * math.pi * k / SEGMENTS
        p = list(pose)
        p[0] = cx + RADIUS * math.cos(a)
        p[1] = cy + RADIUS * math.sin(a)
        return p

    rtde_c.moveL(waypoint(0), speed=0.25)          # onto the circle
    for k in range(1, SEGMENTS + 1):
        rtde_c.moveL(waypoint(k), speed=0.25)
        if k % 6 == 0:
            print(f"{k}/{SEGMENTS} segments")

    rtde_c.moveJ(work, speed=1.0)                  # back to centre pose
    print("circle complete")
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
