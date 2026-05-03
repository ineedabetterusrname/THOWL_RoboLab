import pybullet as p
import pybullet_data
import time
import numpy as np
import os
import socket
import json
import errno

class SimRobot:
    """
    Robust PyBullet Simulation with defensive math and GUI orbiting.
    This class handles the physics simulation of the UR10e robot.
    It also acts as a TCP Server to send data to Unity.
    """
    def __init__(self):
        print("SIM: Starting PyBullet GUI...")
        
        # 1. Start the Physics Engine
        try:
            self.physicsClient = p.connect(p.GUI)
        except Exception as e:
            print(f"SIM: GUI failed, falling back to DIRECT: {e}")
            self.physicsClient = p.connect(p.DIRECT)
            
        # 2. Setup the Environment
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        
        # 3. Load the Robot Model (URDF)
        # We look for the URDF file in the models directory relative to this script.
        current_dir = os.path.dirname(__file__)
        urdf_path = os.path.abspath(os.path.join(current_dir, "..", "models", "ur10e_with_gripper.urdf"))
        print(f"SIM: Loading URDF from {urdf_path}")
        
        self.robot_id = p.loadURDF(urdf_path, [0, 0, 0], useFixedBase=True, flags=0)
        
        if self.robot_id < 0:
            print("SIM: FAILED TO LOAD ROBOT!")
            return

        # 4. Identify Joints and Uncap Limits
        self.joint_indices = []
        self.gripper_indices = []
        self.ee_index = -1 # ID for the Tool/Flange (End Effector)
        
        num_joints = p.getNumJoints(self.robot_id)
        
        for i in range(num_joints):
            info = p.getJointInfo(self.robot_id, i)
            joint_name = info[1].decode("utf-8")
            joint_type = info[2]
            
            p.changeDynamics(self.robot_id, i, maxJointVelocity=50.0)
            
            if joint_type == p.JOINT_REVOLUTE:
                if "shoulder" in joint_name or "elbow" in joint_name or "wrist" in joint_name:
                    self.joint_indices.append(i)
            
            if joint_type == p.JOINT_PRISMATIC:
                if "finger" in joint_name:
                    self.gripper_indices.append(i)
            
            if joint_name == "tool0" or joint_name == "flange-tool0" or joint_name == "ee_joint":
                self.ee_index = i
        
        if self.ee_index == -1:
            self.ee_index = num_joints - 1
        
        self.movable_indices = [
            i for i in range(num_joints) 
            if p.getJointInfo(self.robot_id, i)[2] != p.JOINT_FIXED
        ]
        
        # 6. Set Starting Pose
        starting_q = [0.0, -1.2, 1.2, -1.5, -1.5, 0.0]
        for i, idx in enumerate(self.joint_indices):
            if i < len(starting_q):
                p.resetJointState(self.robot_id, idx, starting_q[i])
        
        # 7. Initialize Target Variables
        state = p.getLinkState(self.robot_id, self.ee_index)
        self.tcp_pos = list(state[4]) 
        self.tcp_orn = list(state[5]) 
        
        self.target_vel = np.zeros(6) 
        self.target_gripper = 0.0     
        self.last_update = time.time()
        
        # 8. Setup Visualizer Camera
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.resetDebugVisualizerCamera(cameraDistance=1.5, cameraYaw=50, cameraPitch=-25, cameraTargetPosition=[0,0,0.5])
        
        # 9. Start Unity Bridge Server (TCP)
        self.unity_mode = True
        self.server_socket = None
        self.conn = None
        if self.unity_mode:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(("0.0.0.0", 8080))
                self.server_socket.listen(1)
                self.server_socket.setblocking(False)
                print("SIM: Unity Bridge Server Waiting on Port 8080...")
            except Exception as e:
                print(f"SIM: Failed to start Unity Bridge: {e}")

        # 10. Home Position
        self.home_pos = list(self.tcp_pos)
        self.home_orn = list(self.tcp_orn)
        self.home_grip = 0.0
        
        # 11. CREATE GUI
        self.slider_ids = {}
        self.setup_ui(self.home_pos, self.home_orn, self.home_grip)

        # 12. DEBUG GHOST OBJECT
        ghost_visual = p.createVisualShape(shapeType=p.GEOM_BOX, halfExtents=[0.05, 0.05, 0.005], rgbaColor=[0, 1, 1, 0.4])
        self.ghost_id = p.createMultiBody(baseVisualShapeIndex=ghost_visual)
        p.setCollisionFilterGroupMask(self.ghost_id, -1, 0, 0)
        
        self.debug_visible = True
        self.control_mode = "SLIDER" 

    def setup_ui(self, pos, orn, grip):
        p.removeAllUserParameters()
        self.btn_reset_id = p.addUserDebugParameter("RESET ROBOT", 1, 0, 0)
        self.btn_home_id = p.addUserDebugParameter("SET AS HOME", 1, 0, 0)
        self.btn_debug_id = p.addUserDebugParameter("TOGGLE DEBUG", 1, 0, 0) 
        
        self.btn_reset_count = 0 
        self.btn_home_count = 0
        self.btn_debug_count = 0
        
        euler = p.getEulerFromQuaternion(orn)
        self.slider_ids['x'] = p.addUserDebugParameter("Tx", -2.0, 2.0, pos[0])
        self.slider_ids['y'] = p.addUserDebugParameter("Ty", -2.0, 2.0, pos[1])
        self.slider_ids['z'] = p.addUserDebugParameter("Tz", 0.0, 2.0, pos[2])
        self.slider_ids['rx'] = p.addUserDebugParameter("Rx", -3.14, 3.14, euler[0])
        self.slider_ids['ry'] = p.addUserDebugParameter("Ry", -3.14, 3.14, euler[1])
        self.slider_ids['rz'] = p.addUserDebugParameter("Rz", -3.14, 3.14, euler[2])
        self.slider_ids['grip'] = p.addUserDebugParameter("Gripper", 0.0, 0.04, grip)

    def update(self):
        if not p.isConnected(self.physicsClient): 
            return

        try:
            now = time.time()
            dt = now - self.last_update
            self.last_update = now
            
            # Read Buttons
            curr_reset_clicks = p.readUserDebugParameter(self.btn_reset_id)
            curr_home_clicks = p.readUserDebugParameter(self.btn_home_id)
            curr_debug_clicks = p.readUserDebugParameter(self.btn_debug_id)
            
            if curr_reset_clicks > self.btn_reset_count:
                self.tcp_pos = list(self.home_pos)
                self.tcp_orn = list(self.home_orn)
                self.target_gripper = self.home_grip
                self.setup_ui(self.home_pos, self.home_orn, self.home_grip)
                return 
            
            if curr_home_clicks > self.btn_home_count:
                self.btn_home_count = curr_home_clicks
                self.home_pos = list(self.tcp_pos)
                self.home_orn = list(self.tcp_orn)
                self.home_grip = self.target_gripper

            if curr_debug_clicks > self.btn_debug_count:
                self.btn_debug_count = curr_debug_clicks
                self.debug_visible = not self.debug_visible
                alpha = 0.4 if self.debug_visible else 0.0
                p.changeVisualShape(self.ghost_id, -1, rgbaColor=[0, 1, 1, alpha])

            if self.control_mode == "SLIDER":
                self.tcp_pos = [
                    p.readUserDebugParameter(self.slider_ids['x']),
                    p.readUserDebugParameter(self.slider_ids['y']),
                    p.readUserDebugParameter(self.slider_ids['z'])
                ]
                self.tcp_orn = p.getQuaternionFromEuler([
                    p.readUserDebugParameter(self.slider_ids['rx']),
                    p.readUserDebugParameter(self.slider_ids['ry']),
                    p.readUserDebugParameter(self.slider_ids['rz'])
                ])
                self.target_gripper = p.readUserDebugParameter(self.slider_ids['grip'])

            p.resetBasePositionAndOrientation(self.ghost_id, self.tcp_pos, self.tcp_orn)

            # Unity Bridge
            if self.unity_mode and self.server_socket:
                if not self.conn:
                    try:
                        c, addr = self.server_socket.accept()
                        c.setblocking(False)
                        self.conn = c
                    except: pass
                
                if self.conn and (now - getattr(self, 'last_net_tx', 0) > 0.033):
                    try:
                        self.last_net_tx = now
                        states = p.getJointStates(self.robot_id, self.joint_indices + self.gripper_indices)
                        angles = [s[0] for s in states]
                        data = json.dumps({"q": angles}) + "\n"
                        self.conn.sendall(data.encode('utf-8'))
                    except:
                        self.conn = None

            # Visual Debugging
            if self.debug_visible:
                p.addUserDebugLine(self.tcp_pos, p.multiplyTransforms(self.tcp_pos, self.tcp_orn, [0.15,0,0], [0,0,0,1])[0], [1,0,0], 6, 0.1)
                p.addUserDebugLine(self.tcp_pos, p.multiplyTransforms(self.tcp_pos, self.tcp_orn, [0,0.15,0], [0,0,0,1])[0], [0,1,0], 6, 0.1)
                p.addUserDebugLine(self.tcp_pos, p.multiplyTransforms(self.tcp_pos, self.tcp_orn, [0,0,0.15], [0,0,0,1])[0], [0,0,1], 6, 0.1)
            
            # Inverse Kinematics
            target_joint_positions = p.calculateInverseKinematics(
                self.robot_id, self.ee_index, self.tcp_pos, self.tcp_orn,
                maxNumIterations=50, residualThreshold=0.001
            )
            
            joint_map = {idx: target_joint_positions[i] for i, idx in enumerate(self.movable_indices)}
            arm_targets = [joint_map[idx] for idx in self.joint_indices]
            
            p.setJointMotorControlArray(
                self.robot_id, self.joint_indices, 
                controlMode=p.POSITION_CONTROL,
                targetPositions=arm_targets,
                forces=[10000]*len(self.joint_indices), 
                positionGains=[0.1]*len(self.joint_indices),
                velocityGains=[1.2]*len(self.joint_indices)
            )
            
            if self.gripper_indices:
                p.setJointMotorControlArray(
                    self.robot_id, self.gripper_indices,
                    controlMode=p.POSITION_CONTROL,
                    targetPositions=[self.target_gripper] * len(self.gripper_indices),
                    forces=[1000] * len(self.gripper_indices)
                )
            
            p.stepSimulation()
            time.sleep(0.001)
            
        except Exception as e:
            print(f"SIM Loop Error: {e}")
            time.sleep(1) 

    def set_control_mode(self, mode):
        if mode == "SLIDER" and self.control_mode == "VELOCITY":
            self.setup_ui(self.tcp_pos, self.tcp_orn, self.target_gripper)
        self.control_mode = mode

    def speedL(self, velocities, accel=0.1, time_val=0.1):
        self.control_mode = "VELOCITY"
        dt = 0.05 
        self.tcp_pos[0] += velocities[0] * dt
        self.tcp_pos[1] += velocities[1] * dt
        self.tcp_pos[2] += velocities[2] * dt
        curr_euler = p.getEulerFromQuaternion(self.tcp_orn)
        new_euler = [curr_euler[i] + velocities[i+3] * dt for i in range(3)]
        self.tcp_orn = p.getQuaternionFromEuler(new_euler)

    def stopScript(self):
        if p.isConnected(self.physicsClient):
            p.disconnect()

class RTDEControlInterface:
    def __init__(self, ip): self.robot = SimRobot()
    def speedL(self, v, a=0.1, s=0.1): self.robot.speedL(v, a, s)
    def update(self): self.robot.update()
    def stopScript(self): self.robot.stopScript()
    def set_control_mode(self, mode): self.robot.set_control_mode(mode)

class RTDEReceiveInterface:
    def __init__(self, ip): pass
    def getActualTCPPose(self): return [0,0,0,0,0,0]

if __name__ == "__main__":
    sim = SimRobot()
    while True:
        sim.update()
