import pybullet as p
import pybullet_data
import time
import os
import numpy as np

# VR Controller ID Mapping (Generic OpenVR/Touch)
BUTTON_A = 7
BUTTON_TRIGGER = 33 

class VRRobot:
    def __init__(self):
        print("VR: Connecting to OpenVR (SteamVR)...")
        try:
            self.physicsClient = p.connect(p.VR)
        except:
            self.physicsClient = -1
        
        if self.physicsClient < 0:
            print("VR: Failed to connect! falling back to GUI.")
            self.physicsClient = p.connect(p.GUI)
        
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        
        # Load URDF relative to this script
        current_dir = os.path.dirname(__file__)
        urdf_path = os.path.abspath(os.path.join(current_dir, "..", "models", "ur10e_with_gripper.urdf"))
        print(f"VR: Loading URDF from {urdf_path}")
        self.robot_id = p.loadURDF(urdf_path, [0, 0, 0], useFixedBase=True, flags=0)
        
        self.joint_indices = []
        self.gripper_indices = []
        self.ee_index = -1
        
        num_joints = p.getNumJoints(self.robot_id)
        for i in range(num_joints):
            info = p.getJointInfo(self.robot_id, i)
            joint_name = info[1].decode('utf-8')
            joint_type = info[2]
            
            if joint_type == p.JOINT_REVOLUTE:
                self.joint_indices.append(i)
            if "finger_joint" in joint_name and joint_type == p.JOINT_PRISMATIC:
                self.gripper_indices.append(i)
            if joint_name == "tool0" or joint_name == "flange-tool0" or joint_name == "ee_joint":
                self.ee_index = i

        if self.ee_index == -1: self.ee_index = num_joints - 1
        self.movable_indices = [i for i in range(num_joints) if p.getJointInfo(self.robot_id, i)[2] != p.JOINT_FIXED]
        
        self.home_q = [0.0, -1.2, 1.2, -1.5, -1.5, 0.0]
        self.reset_robot()
        
        print("VR READY. Controls: Right Controller = Arm, Trigger = Gripper, Button A = Reset.")

    def reset_robot(self):
        for i, idx in enumerate(self.joint_indices):
            if i < len(self.home_q):
                p.resetJointState(self.robot_id, idx, self.home_q[i])

    def run(self):
        while p.isConnected():
            events = p.getVREvents()
            controller_pos = controller_orn = None
            trigger_val = 0.0
            reset_pressed = False
            
            for e in events:
                if e[6].get(BUTTON_A) == 1.0: reset_pressed = True
                if e[1] & p.VR_DEVICE_CONTROLLER:
                    controller_pos, controller_orn = e[2], e[3]
                    trigger_val = e[6].get(33, 0.0) 

            if reset_pressed: self.reset_robot()
            
            if controller_pos:
                target_joint_positions = p.calculateInverseKinematics(
                    self.robot_id, self.ee_index, controller_pos, controller_orn, maxNumIterations=10
                )
                joint_map = {idx: target_joint_positions[i] for i, idx in enumerate(self.movable_indices)}
                arm_targets = [joint_map[idx] for idx in self.joint_indices]
                
                p.setJointMotorControlArray(
                    self.robot_id, self.joint_indices, controlMode=p.POSITION_CONTROL,
                    targetPositions=arm_targets, forces=[500]*len(self.joint_indices)
                )
                
                target_gripper = 0.04 * (1.0 - trigger_val)
                if self.gripper_indices:
                     p.setJointMotorControlArray(
                        self.robot_id, self.gripper_indices, controlMode=p.POSITION_CONTROL,
                        targetPositions=[target_gripper] * len(self.gripper_indices), forces=[100] * len(self.gripper_indices)
                    )

            p.stepSimulation()
            time.sleep(0.01)

if __name__ == "__main__":
    sim = VRRobot()
    sim.run()
