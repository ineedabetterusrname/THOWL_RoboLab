# 🤖 Interactive Robot: Gesture Teleoperation Template

This project is a modular template designed for students to understand and experiment with Human-Robot Collaboration (HRC) using hand tracking and the UR10e robot.

It supports both a **Physics Simulation (PyBullet)** and the **Real UR10e Robot**.

---

## 🛠️ 1. Installation

1.  **Install Python 3.8+**
2.  **Install Dependencies**:
    Open a terminal in this folder and run:
    ```powershell
    pip install -r requirements.txt
    ```

---

## 🎮 2. Simulation Mode (PyBullet)

*Test the system in a safe virtual environment.*

1.  **Navigate to scripts**:
    ```powershell
    cd scripts
    ```
2.  **Run the Simulation**:
    ```powershell
    python main_sim.py
    ```
3.  **Features**:
    *   **Hand Tracking**: Controls the robot velocity using your webcam.
    *   **Debug Sliders**: If no hands are detected, you can move the robot using the PyBullet GUI sliders.
    *   **Ghost Target**: Visualizes the target position and orientation.
    *   **Unity Bridge**: Automatically starts a TCP server on port 8080 to stream joint data to external applications (like Unity VR).

---

## 🤖 3. Real Robot Control

*Control the physical UR10e robot in the lab.*

1.  **Connect to Network**: Ensure your PC is connected to the same network as the UR10e.
2.  **Set IP**: Open `scripts/main_real.py` and set `robot_ip` to your robot's IP (e.g., `192.168.x.x`).
3.  **Run the Script**:
    ```powershell
    python main_real.py
    ```

---

## 📂 Project Structure

*   `scripts/main_sim.py`: Entry point for simulation mode.
*   `scripts/main_real.py`: Entry point for real robot mode.
*   `scripts/ur10e_control.py`: The core simulation and control interface.
*   `models/`: Contains URDF files and 3D meshes for the UR10e and gripper.
*   `requirements.txt`: Python libraries needed.

---

## 🖐️ Controls

*   **Right Hand**: Controls translation (Left/Right, Forward/Back, Up/Down).
*   **Left Hand**: Controls rotation (Roll, Pitch, Yaw).
*   **Safety (Fist)**: Close either hand into a fist to immediately stop the robot.
