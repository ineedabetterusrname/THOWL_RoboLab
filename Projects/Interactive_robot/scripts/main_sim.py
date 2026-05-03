import cv2
import mediapipe as mp
import numpy as np
import ur10e_control as rtde_control
import ur10e_control as rtde_receive
import time
import math

# -----------------------
# Robot connection setup (SIMULATION)
# -----------------------
robot_ip = "127.0.0.1"
rtde_c = rtde_control.RTDEControlInterface(robot_ip)
rtde_r = rtde_receive.RTDEReceiveInterface(robot_ip)

# -----------------------
# SPEED SETTINGS
# -----------------------
MAX_LINEAR_SPEED_XY = 0.5      # m/s
MAX_LINEAR_SPEED_Z  = 0.5      # m/s
MAX_ANGULAR_SPEED   = 1.0      # rad/s (rotation)

# Deadzone sizes
NEUTRAL_RADIUS_TRANSL = 80     
NEUTRAL_RADIUS_ROT    = 80     

# Z-axis (depth) deadzone
Z_NEUTRAL = -0.05
Z_DEADZONE = 0.01
Z_DISPLAY_RANGE = 0.5

# -----------------------
# Mediapipe setup
# -----------------------
mp_hands = mp.solutions.hands
HAND_CONNECTIONS = mp_hands.HAND_CONNECTIONS

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Fist detection threshold
FIST_THRESHOLD = 0.07

def is_fist(hand_landmarks):
    fingers = [(8,5),(12,9),(16,13),(20,17)]
    total_dist = 0.0
    for tip, base in fingers:
        t = hand_landmarks.landmark[tip]
        b = hand_landmarks.landmark[base]
        total_dist += math.dist([t.x, t.y],[b.x, b.y])
    return (total_dist / 4.0) < FIST_THRESHOLD


print("SIMULATION READY — Right hand = translation, Left hand = rotation")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera error")
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    mid_x = w // 2
    cy = int(h // 2.5)
    left_center_x = mid_x // 2
    right_center_x = mid_x + mid_x // 2

    # Mediapipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    # UI Overlay
    cv2.line(frame, (mid_x, 0), (mid_x, h), (0, 255, 255), 4)
    cv2.circle(frame, (left_center_x, cy), NEUTRAL_RADIUS_ROT, (255, 150, 0), 2)
    cv2.circle(frame, (right_center_x, cy), NEUTRAL_RADIUS_TRANSL, (0, 255, 255), 2)

    vx = vy = vz = 0.0
    roll = pitch = yaw = 0.0
    left_fist = right_fist = False

    if results.multi_hand_landmarks and results.multi_handedness:
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            hand_label = results.multi_handedness[i].classification[0].label

            if is_fist(hand_landmarks):
                if hand_label == "Left": left_fist = True
                else: right_fist = True

            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]
            tip = hand_landmarks.landmark[8]
            px, py = int(tip.x * w), int(tip.y * h)
            depth_offset = tip.z - Z_NEUTRAL

            if abs(depth_offset) < Z_DEADZONE:
                z_color = (255, 0, 0)
            else:
                z_color = (0,255,0) if depth_offset < 0 else (0,0,255)

            for (a,b) in HAND_CONNECTIONS:
                x1,y1 = pts[a]
                x2,y2 = pts[b]
                cv2.line(frame, (x1,y1), (x2,y2), z_color, 6, cv2.LINE_AA)

            for x,y in pts:
                cv2.circle(frame, (x,y), 4, (255,255,255), -1)

            # Z Bar Visualization
            normalized = np.clip((-depth_offset)/Z_DISPLAY_RANGE, -1, 1)
            bar_h, bar_w = int(h * 0.35), 18
            bar_x = 40 if hand_label == "Left" else w - 40 - bar_w
            bar_y = cy - bar_h//2

            cv2.rectangle(frame, (bar_x-2,bar_y-2), (bar_x+bar_w+2,bar_y+bar_h+2),(50,50,50),-1)
            fill_mid = bar_y + bar_h//2
            fill_offset = int(normalized * (bar_h//2))
            fill_y = fill_mid - fill_offset

            if normalized >= 0:
                cv2.rectangle(frame,(bar_x,fill_y),(bar_x+bar_w,fill_mid),(0,255,0),-1)
            else:
                cv2.rectangle(frame,(bar_x,fill_mid),(bar_x+bar_w,fill_y),(0,0,255),-1)

            # Control Logic
            if hand_label == "Right":  # Translation
                dx, dy = px - right_center_x, py - cy
                dist = math.hypot(dx, dy)
                if dist > NEUTRAL_RADIUS_TRANSL:
                    norm = min((dist - NEUTRAL_RADIUS_TRANSL) / (mid_x - NEUTRAL_RADIUS_TRANSL), 1.0)
                    vx = (dx/dist) * norm * MAX_LINEAR_SPEED_XY
                    vy = -(dy/dist) * norm * MAX_LINEAR_SPEED_XY
                if abs(depth_offset) > Z_DEADZONE:
                    z_sens = 2.5 if depth_offset > 0 else 1.0
                    vz = -depth_offset * z_sens * MAX_LINEAR_SPEED_Z
                    vz = float(np.clip(vz, -MAX_LINEAR_SPEED_Z, MAX_LINEAR_SPEED_Z))
            else:  # Rotation
                dx, dy = px - left_center_x, py - cy
                dist = math.hypot(dx, dy)
                if dist > NEUTRAL_RADIUS_ROT:
                    norm = min((dist - NEUTRAL_RADIUS_ROT) / (mid_x - NEUTRAL_RADIUS_ROT), 1.0)
                    roll = (dx/dist) * norm * MAX_ANGULAR_SPEED
                    pitch = -(dy/dist) * norm * MAX_ANGULAR_SPEED
                if abs(depth_offset) > Z_DEADZONE:
                    yaw = -depth_offset * MAX_ANGULAR_SPEED
                    yaw = float(np.clip(yaw, -MAX_ANGULAR_SPEED, MAX_ANGULAR_SPEED))

    if left_fist or right_fist:
        vx = vy = vz = roll = pitch = yaw = 0
        cv2.putText(frame, "FIST - STOP", (30,60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)

    try:
        if results.multi_hand_landmarks:
            rtde_c.speedL([vx,vy,vz, roll,pitch,yaw], 0.1, 0.1)
        else:
            rtde_c.set_control_mode("SLIDER")
        rtde_c.update() 
    except Exception as e:
        print("RTDE ERROR:", e)

    cv2.imshow("Interactive Robot Simulation", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

rtde_c.stopScript()
cap.release()
cv2.destroyAllWindows()
