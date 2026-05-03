# 🤖 TH OWL Robot Lab: Beginner's Kit

Welcome to the **Robo Lab Projects** repository! This is a centralized hub for students and researchers working with robotics, computer vision, and AI at TH OWL. 

Whether you are here for a workshop, a semester project, or independent research, this kit provides everything you need to get the robot moving safely and effectively.

---

## 📡 Lab Essentials

Before you start, ensure you are connected to the internal lab network.

| Resource | Detail |
| :--- | :--- |
| **Wi-Fi SSID** | `robot-wifi` |
| **Wi-Fi Password** | See label on the physical router in the lab |
| **Robot Model** | Universal Robots UR10e (Cobot) |
| **Default Robot IP** | `192.168.x.x` (Check the Teach Pendant) |

> **Note:** For security, specific login credentials for the Lab PCs and Tapo cameras are not stored in this repository. Please consult the lab supervisor or check the physical `Documentation` folder in the lab.

---

## 🛡️ Safety First (The Golden Rules)

The UR10e is a "Collaborative Robot" (Cobot), but it is still a powerful machine. **Safety is your priority.**

1.  **Emergency Stop:** Locate the red E-Stop button on the Teach Pendant before every run.
2.  **Remote Control Mode:** To control the robot via Python, the Teach Pendant must be set to **Remote Control** mode.
3.  **Clear Workspace:** Ensure no people or expensive equipment are within the "Reach Zone" (~1.3m) of the robot.
4.  **Low Speed First:** Always test new code with the speed slider set to **10% or lower** on the Teach Pendant.

---

## 📂 Project Roadmap

This repository is organized into modular projects. Start with the **Python Template** if you are a beginner.

### 🐣 [A. Python Template](./UR10e_Documentation/Python_Template/)
The absolute basics. A single script to connect to the robot and perform a simple move. Use this to verify your connection.
*   **Key Tool:** `ur_rtde` library.

### 🖐️ [B. Interactive Robot](./Projects/Interactive_robot/)
The "Gesture Teleoperation" system. Control the UR10e in real-time using your hands via a webcam.
*   **Key Tools:** Mediapipe (Hand Tracking), PyBullet (Physics Simulation).

### 👁️ [C. Tapo Vision Kit](./Projects/Tapo_camera/)
Advanced vision tools for the TP-Link Tapo C110. Includes AprilTag calibration for high-accuracy robotic vision.
*   **Key Tools:** OpenCV, AprilTag.

### 🧠 [D. AI Camera Integration](./Projects/Raspberrypi+AI_camera/)
A "Cloud-Brain, Edge-Body" project using Raspberry Pi Zero 2 W and the AI Camera (IMX500) to create a self-learning robot powered by Gemini 1.5 Pro.

---

## 🛠️ Setting Up Your Environment

To run the python projects in this lab, we recommend using **Python 3.10+**.

1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/ineedabetterusrname/THOWL_RoboLab.git
    cd THOWL_RoboLab
    ```
2.  **Install Base Requirements**:
    Each project has its own `requirements.txt` or README. However, for most robot tasks, you will need:
    ```bash
    pip install ur_rtde opencv-python numpy
    ```

---

## 🎓 For Students: How to Contribute

We encourage students to document their work here!
1.  **Modular Folders**: Create a new folder under `Projects/` for your task.
2.  **Documentation**: Every project **must** include a `README.md` explaining how to run it.
3.  **No Secrets**: Never commit passwords or specific IP addresses to GitHub. Use placeholders (e.g., `YOUR_IP`).

---

**Happy Coding!** 🤖🚀
*TH OWL - Architecture & Robotics*
