# ============================================================
# SAMPLE 1 - FIRST MOVES
# Connect, read the robot state, do a joint move and a straight
# TCP move, then return. Works on the real UR10e and in this
# simulator without changes.
# ============================================================
import rtde_control
import rtde_receive
import math

ROBOT_IP = "YOUR_ROBOT_IP"   # ignored by the simulator

def main():
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

    # --- read where the robot is right now -------------------
    q = rtde_r.getActualQ()
    print("joints [deg]:", [round(math.degrees(v), 1) for v in q])
    tcp = rtde_r.getActualTCPPose()
    print("tcp x/y/z [m]:", [round(v, 3) for v in tcp[:3]])

    # --- a safe joint-space "work" pose (moveJ = fast, curved)
    work = [0.0, -1.31, -1.75, -1.66, 1.57, 0.0]
    rtde_c.moveJ(work, speed=1.0, acceleration=1.4)

    # --- straight-line TCP moves (moveL = slower, exact path)
    pose = rtde_r.getActualTCPPose()
    pose[2] -= 0.15                      # 15 cm straight down
    rtde_c.moveL(pose, speed=0.25, acceleration=1.2)
    pose[1] += 0.20                      # 20 cm sideways (+Y)
    rtde_c.moveL(pose, speed=0.25, acceleration=1.2)

    # --- back to the work pose and report --------------------
    rtde_c.moveJ(work, speed=1.0)
    print("final tcp [m]:", [round(v, 3) for v in rtde_r.getActualTCPPose()[:3]])
    rtde_c.disconnect()

if __name__ == "__main__":
    main()
