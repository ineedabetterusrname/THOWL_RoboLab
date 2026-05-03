import rtde_control
import rtde_receive
import time

# =============================================================================
# UR10e BASIC MOVEMENT TEMPLATE
# =============================================================================
# This script demonstrates the absolute basics of connecting to and moving 
# a Universal Robot (UR10e) using the 'ur_rtde' library.
#
# Prerequisite: pip install ur_rtde
# =============================================================================

# 1. SET THE ROBOT IP ADDRESS
# In the lab, this is usually 192.168.x.x or similar.
# Ensure your computer is on the same network as the robot.
ROBOT_IP = "YOUR_ROBOT_IP" 

# Note: This is a very basic template. In practice, you should add error handling. 

def main():
    try:
        print(f"Connecting to robot at {ROBOT_IP}...")
        
        # 2. INITIALIZE INTERFACES
        # Control Interface: Used to send move commands
        rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
        # Receive Interface: Used to read data (position, speeds, etc.)
        rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
        
        print("Connected successfully!")

        # 3. READ CURRENT POSITION
        # Read joint positions (Radians: [Base, Shoulder, Elbow, Wrist1, Wrist2, Wrist3])
        actual_q = rtde_r.getActualQ()
        print(f"\nCurrent Joint Positions (rad): {actual_q}")
        
        # Read TCP Pose (Meters/Radians: [X, Y, Z, Rx, Ry, Rz])
        actual_tcp = rtde_r.getActualTCPPose()
        print(f"Current TCP Pose (m/rad): {actual_tcp}")

        # 4. DEFINE TARGET POSITIONS
        # Joint Target (moveJ): Good for large, safe movements.
        # This is a slightly offset 'Home' position.
        target_q = [0.0, -1.57, 1.57, -1.57, -1.57, 0.0]
        
        # Linear Target (moveL): Moves the tool in a straight line.
        # We take the current pose and move it 10cm up in Z.
        target_tcp = list(actual_tcp)
        target_tcp[2] += 0.1 

        # 5. EXECUTE MOVEMENTS
        # speed: rad/s for moveJ, m/s for moveL
        # acceleration: rad/s^2 for moveJ, m/s^2 for moveL
        
        print("\nMoving to Joint Target (moveJ)...")
        rtde_c.moveJ(target_q, speed=0.5, acceleration=0.5)
        
        print("Moving 10cm up in Linear Space (moveL)...")
        rtde_c.moveL(target_tcp, speed=0.1, acceleration=0.1)

        # 6. STOPPING
        print("\nMovement complete. Disconnecting.")
        rtde_c.stopScript()

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        print("Check if the robot is in 'Remote Control' mode on the Teach Pendant.")

if __name__ == "__main__":
    main()
