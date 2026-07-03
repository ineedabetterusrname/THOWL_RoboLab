# ============================================================
# ROBOTIC BRICKLAYING - running-bond wall assembly
# ------------------------------------------------------------
# The classic AEC robotics demo (Gramazio Kohler's "programmed
# wall"): the robot picks bricks from a supply station and lays
# a small wall in running bond, course by course. The wall
# geometry is *computed*, not taught - change the parameters
# and the same code builds a different wall.
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

# ---- wall parameters (metres) ------------------------------
BRICK_L = 0.090                # brick length (along the wall)
BRICK_H = 0.040                # course height
COURSES = 3                    # number of courses (rows)
BRICKS_PER_COURSE = 3
JOINT_GAP = 0.010              # head-joint gap between bricks

# ---- motion parameters -------------------------------------
VEL_J, VEL_L, VEL_FINE = 1.0, 0.25, 0.08
HOVER = 0.10                   # travel height above pick/place [m]
WORK_POSE = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]

def move_pick_place(rtde_c, src, dst, action_close, action_open):
    """One brick: hover->descend->grip at src, hover->descend->release at dst."""
    for target, action in ((src, action_close), (dst, action_open)):
        above = list(target); above[2] += HOVER
        rtde_c.moveL(above, speed=VEL_L)
        rtde_c.moveL(target, speed=VEL_FINE)   # slow near material
        print("   ", action)
        time.sleep(0.4)                        # gripper I/O placeholder
        rtde_c.moveL(above, speed=VEL_L)

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    rtde_c.moveJ(WORK_POSE, speed=VEL_J)
    base = rtde_r.getActualTCPPose()           # everything is relative

    # supply station: one fixed pick point, 15 cm to -Y, 20 cm down
    pick = list(base)
    pick[1] -= 0.15
    pick[2] -= 0.20

    # wall: first brick sits 8 cm to +Y of the work pose, same height
    wall_y0 = base[1] + 0.08
    wall_z0 = base[2] - 0.20

    total = 0
    for course in range(COURSES):
        # running bond: every second course shifts by half a brick
        offset = (BRICK_L + JOINT_GAP) / 2 if course % 2 else 0.0
        print(f"course {course + 1}/{COURSES}")
        for i in range(BRICKS_PER_COURSE):
            place = list(base)
            place[1] = wall_y0 + offset + i * (BRICK_L + JOINT_GAP)
            place[2] = wall_z0 + course * BRICK_H
            move_pick_place(rtde_c, pick, place,
                            f"grip brick {total + 1}", f"release at course {course + 1}, bay {i + 1}")
            total += 1

    rtde_c.moveJ(WORK_POSE, speed=VEL_J)
    print(f"wall complete: {total} bricks, {COURSES} courses")
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
