# 🐍 UR10e Python Movement Template

This folder contains a simple, well-commented Python template for controlling the UR10e robot via the **RTDE (Real-Time Data Exchange)** protocol.

## 🚀 How to use

1.  **Install the library**:
    ```bash
    pip install ur_rtde
    ```
2.  **Configure the IP**:
    Open `ur10e_basic_template.py` and change `ROBOT_IP` to match the IP shown on the robot's Teach Pendant (e.g., `192.168.x.x`).
3.  **Run the script**:
    ```bash
    python ur10e_basic_template.py
    ```

## 📂 Project Structure

*   `ur10e_basic_template.py`: The main Python script with movement commands.
*   `README.md`: This guide.

## 📖 Key Commands Explained

*   `RTDEControlInterface(IP)`: Connects to the robot to send movement commands.
*   `RTDEReceiveInterface(IP)`: Connects to the robot to read status data (position, temperature, etc.).
*   `moveJ(joints, speed, accel)`: Moves the robot to specific joint angles. Fast and safe for large movements.
*   `moveL(pose, speed, accel)`: Moves the tool center point (TCP) in a straight line to a specific coordinate.
*   `getActualQ()`: Returns the current joint angles in Radians.
*   `getActualTCPPose()`: Returns the current [X, Y, Z, Rx, Ry, Rz] position of the tool.

## ⚠️ Safety First
*   Always have the **Emergency Stop** button within reach.
*   Ensure the robot is in **Remote Control** mode on the Teach Pendant.
*   Check that the robot's workspace is clear before running the script.
