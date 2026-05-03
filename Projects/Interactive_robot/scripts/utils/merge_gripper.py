import re
import os

# ------------------------------------------------------------------
# URDF MERGER SCRIPT (Template)
# ------------------------------------------------------------------
# This script stitches two URDF files together:
# 1. The UR10e Robot (Arm)
# 2. The 2FG7 Gripper
# ------------------------------------------------------------------

def filter_urdf_lines(content, is_gripper=False):
    lines = content.splitlines()
    filtered_lines = []
    skip_mode = False
    skip_tag = ""
    
    for line in lines:
        stripped = line.strip()
        if not skip_mode:
            if stripped.startswith("<gazebo") or stripped.startswith("<transmission") or stripped.startswith("<material"):
                skip_mode = True
                skip_tag = stripped.split()[0][1:] 
                if "/>" in stripped: skip_mode = False
                continue
            if is_gripper and ("<link name=\"world\"" in line or "<joint name=\"world_joint\"" in line):
                 skip_mode = True
                 skip_tag = "link" if "link" in line else "joint"
                 if "/>" in stripped: skip_mode = False
                 continue
        else:
            if f"</{skip_tag}>" in stripped: skip_mode = False
            continue

        if is_gripper:
            if "<robot" in line or "<?xml" in line or "</robot>" in line: continue
            if 'name="base_link"' in line: line = line.replace('name="base_link"', 'gripper_base')
            if 'parent link="base_link"' in line: line = line.replace('parent link="base_link"', 'gripper_base')
            if "package://onrobot_2fg7_description/meshes/" in line:
                line = line.replace("package://onrobot_2fg7_description/meshes/", "gripper_meshes/")
        else:
             if "</robot>" in line: continue

        filtered_lines.append(line)
    return "\n".join(filtered_lines)

def merge(arm_urdf, gripper_urdf, output_urdf):
    if not os.path.exists(arm_urdf) or not os.path.exists(gripper_urdf):
        print(f"Error: Missing input files {arm_urdf} or {gripper_urdf}")
        return

    print(f"Merging {arm_urdf} and {gripper_urdf}...")
    ur10_content = open(arm_urdf, "r", encoding="utf-8").read()
    gripper_content = open(gripper_urdf, "r", encoding="utf-8").read()

    ur10_clean = filter_urdf_lines(ur10_content, is_gripper=False)
    gripper_clean = filter_urdf_lines(gripper_content, is_gripper=True)

    connection_joint = """
      <joint name="tool0_gripper_base" type="fixed">
        <parent link="tool0"/>
        <child link="gripper_base"/>
        <origin xyz="0 0 0" rpy="0 0 0"/>
      </joint>
    """

    final_urdf = ur10_clean + "\n" + connection_joint + "\n" + gripper_clean + "\n</robot>"
    with open(output_urdf, "w", encoding="utf-8") as f:
        f.write(final_urdf)
    print(f"Success! Created: {output_urdf}")

if __name__ == "__main__":
    # Assuming run from scripts/utils/
    models_dir = os.path.join("..", "..", "models")
    merge(
        os.path.join(models_dir, "ur10e.urdf"),
        os.path.join(models_dir, "gripper.urdf"),
        os.path.join(models_dir, "ur10e_with_gripper_new.urdf")
    )
