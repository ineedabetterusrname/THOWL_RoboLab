# ============================================================
# SAMPLE 2 - PICK AND PLACE
# The classic cycle: hover over the pick point, descend straight
# down, "grip", lift, carry to the place point, descend, release.
# time.sleep() stands in for gripper I/O commands.
# ============================================================
import rtde_control
import rtde_receive
import time

ROBOT_IP = "YOUR_ROBOT_IP"   # ignored by the simulator

VEL_J, VEL_L = 1.0, 0.25     # joint speed rad/s, TCP speed m/s
HOVER = 0.15                 # approach height above the object [m]

def descend_and_return(rtde_c, rtde_r, depth, action):
    """Move straight down by depth, do the action, come back up."""
    pose = rtde_r.getActualTCPPose()
    pose[2] -= depth
    rtde_c.moveL(pose, speed=0.1)        # slow near the object
    print(action)
    time.sleep(0.5)                      # gripper open/close placeholder
    pose[2] += depth
    rtde_c.moveL(pose, speed=VEL_L)

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    start = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]
    rtde_c.moveJ(start, speed=VEL_J)

    # pick and place TCP targets, relative to the start pose
    base = rtde_r.getActualTCPPose()
    pick = list(base);  pick[1] -= 0.15   # 15 cm to -Y
    place = list(base); place[1] += 0.25  # 25 cm to +Y

    for i in range(2):                    # two full cycles
        print(f"cycle {i + 1}: pick")
        rtde_c.moveL(pick, speed=VEL_L)
        descend_and_return(rtde_c, rtde_r, HOVER, "  gripper CLOSE")
        print(f"cycle {i + 1}: place")
        rtde_c.moveL(place, speed=VEL_L)
        descend_and_return(rtde_c, rtde_r, HOVER, "  gripper OPEN")

    rtde_c.moveJ(start, speed=VEL_J)
    print("done")
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
