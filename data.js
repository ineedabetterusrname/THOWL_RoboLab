/* ============================================================
   TH OWL Robo Lab — Site data
   Edit this file to add or change Projects and Hardware entries.
   ============================================================ */

window.RoboLabData = {

  /* --------------------------- REPO ------------------------- */
  repo: "https://github.com/ineedabetterusrname/THOWL_RoboLab",
  branch: "main",

  /* --------------------------- TEMPLATES --------------------- */
  templates: [
    {
      id: "python-template",
      title: "Python Template (UR10e)",
      tag: "Starter",
      tagClass: "tag-navy",
      summary:
        "Single-script template to connect to the UR10e via RTDE and run a verified move. Start here to confirm your network, IP, and Remote Control setup.",
      stack: ["Python 3.10+", "ur_rtde"],
      path: "UR10e_Documentation/Python_Template/",
      file: "ur10e_basic_template.py",
    },
    {
      id: "rhino-template",
      title: "Rhino + Grasshopper Template",
      tag: "Starter",
      tagClass: "tag-teal",
      summary:
        "Reference Rhino model and Grasshopper definition matched to the lab cell. Use this to plan toolpaths in a known-good workspace.",
      stack: ["Rhino 7+", "Grasshopper"],
      path: "UR10e_Documentation/Rhino+Grasshopper_Template/",
      file: "THOWL_RoboLab_UR10e_Template.gh",
    },
  ],

  /* --------------------------- PROJECTS --------------------- */
  projects: [
    {
      id: "interactive-robot",
      number: "01",
      title: "Interactive Robot",
      subtitle: "Gesture Teleoperation",
      tag: "Vision · Real-time",
      tagClass: "tag-amber",
      summary:
        "Control the UR10e in real time with your hands via a webcam. Switch between PyBullet simulation and the real robot. Includes a TCP bridge for streaming joint data to external apps (e.g. Unity VR).",
      tools: ["Mediapipe", "PyBullet", "ur_rtde", "OpenCV"],
      controls: [
        "Right hand → translation (X / Y / Z)",
        "Left hand  → rotation (roll / pitch / yaw)",
        "Fist → immediate stop",
      ],
      path: "Projects/Interactive_robot/",
      ticks: ["SIM", "REAL", "TCP:8080"],
    },
    {
      id: "tapo-vision",
      number: "02",
      title: "Tapo Vision Kit",
      subtitle: "AprilTag calibration for the TP-Link C110",
      tag: "Computer Vision",
      tagClass: "tag-navy",
      summary:
        "Vision utilities for the lab's Tapo C110 cameras: RTSP capture, intrinsic calibration, and AprilTag-based hand-eye / world coordinate alignment for accurate pick targets.",
      tools: ["OpenCV", "AprilTag", "RTSP"],
      controls: [
        "Calibrate camera intrinsics from checkerboard sweeps",
        "Detect AprilTags and solve robot-to-world transform",
        "Stream into the UR10e move script as target poses",
      ],
      path: "Projects/Tapo_camera/",
      ticks: ["RTSP", "INTRINSICS", "TAG36H11"],
    },
    {
      id: "ai-camera",
      number: "03",
      title: "Pi Zero 2 W + AI Camera",
      subtitle: "Cloud-Brain, Edge-Body with Gemini",
      tag: "LLM · Embodied",
      tagClass: "tag-amber",
      summary:
        "Self-correcting pick system. A Raspberry Pi Zero 2 W with the IMX500 captures keyframes; a workstation runs Gemini (2.5 Pro or current) to reason over the scene and emit motion commands the UR10e executes via ur_rtde.",
      tools: ["Raspberry Pi", "IMX500", "Gemini API", "FastAPI"],
      controls: [
        "Pi exposes /snap endpoint for high-res keyframes",
        "Workstation runs Chain-of-Thought reasoning loop",
        "Successful runs stored as few-shot exemplars",
      ],
      path: "Projects/Raspberrypi+AI_camera/",
      file: "UR10e+AI_Camera.md",
      ticks: ["PI ZERO 2W", "IMX500", "GEMINI"],
    },
    {
      id: "hanger",
      number: "04",
      title: "Hanger",
      subtitle: "Suspended-element workflow (Room 4.303)",
      tag: "Fabrication",
      tagClass: "tag-teal",
      summary:
        "Rhino + Grasshopper definition for designing and verifying the hanger setup in room 4.303. Starting point for student work on suspended-element assemblies.",
      tools: ["Rhino", "Grasshopper"],
      controls: [
        "Open hanger_4.303.gh against the matching .3dm",
        "Adapt clamp positions, then export toolpaths",
      ],
      path: "Projects/Hanger/",
      ticks: ["RHINO", "GH"],
    },
    {
      id: "robotic-bricklaying",
      number: "05",
      title: "Robotic Bricklaying",
      subtitle: "Running-bond wall assembly",
      tag: "AEC · Fabrication",
      tagClass: "tag-teal",
      summary:
        "Computed masonry in one Python file: the UR10e picks bricks from a supply point and lays a small wall in running bond, course by course. Wall size, brick dimensions and joint gaps are parameters — change them and the same code builds a different wall. Test it in the web simulator before booking robot time.",
      tools: ["Python", "ur_rtde", "Web simulator"],
      controls: [
        "Edit BRICK_L / COURSES / JOINT_GAP to redesign the wall",
        "time.sleep() placeholders mark the gripper I/O moments",
        "Runs unchanged in the simulator's Code tab and on the real robot",
      ],
      path: "Projects/Robotic_Bricklaying/",
      file: "robotic_bricklaying.py",
      ticks: ["SIM + REAL", "RUNNING BOND", "1 FILE"],
    },
    {
      id: "contour-crafting",
      number: "06",
      title: "Contour Crafting",
      subtitle: "Layered printing toolpath",
      tag: "AEC · Additive",
      tagClass: "tag-amber",
      summary:
        "Construction-scale 3D printing in miniature: the TCP traces a superellipse profile layer by layer with parametric taper, twist and layer height — the exact motion of clay or concrete extrusion printing. Mount a pen instead of a nozzle and it draws its layers on paper.",
      tools: ["Python", "ur_rtde", "Web simulator"],
      controls: [
        "Tune LAYERS / RADIUS / TWIST / SQUARENESS for new geometry",
        "Straight-line moveL segments approximate each closed contour",
        "Extend: trigger an extruder via tool I/O at layer starts",
      ],
      path: "Projects/Contour_Crafting/",
      file: "contour_crafting.py",
      ticks: ["SIM + REAL", "ADDITIVE", "1 FILE"],
    },
    {
      id: "facade-scanning",
      number: "07",
      title: "Façade Scanning",
      subtitle: "Raster survey of a vertical surface",
      tag: "AEC · Inspection",
      tagClass: "tag-navy",
      summary:
        "Robotic building inspection: a wrist-mounted sensor sweeps a façade panel in a boustrophedon raster, pausing at every grid point to capture — the motion pattern behind photogrammetry, thermal QA and NDT surveys. Pairs nicely with the simulator's wrist camera for a live sensor's-eye view.",
      tools: ["Python", "ur_rtde", "Web simulator"],
      controls: [
        "Set PANEL_W / PANEL_H / ROWS / COLS to match the surface",
        "Serpentine ordering minimises travel between captures",
        "Extend: trigger the Tapo / IMX500 camera at each dwell",
      ],
      path: "Projects/Facade_Scanning/",
      file: "facade_scan.py",
      ticks: ["SIM + REAL", "RASTER SCAN", "1 FILE"],
    },
    {
      id: "tapo-camera-access",
      number: "08",
      title: "Tapo Camera Access",
      subtitle: "RTSP camera streams in Python",
      tag: "Computer Vision",
      tagClass: "tag-navy",
      summary:
        "One module and five command-line tools for reading the lab's Tapo cameras over RTSP. Handles the awkward parts for you: a reader thread that always hands back the newest frame instead of a stale buffered one, automatic reconnects, and an HTTP relay so a whole group can watch without exhausting the camera's two-client limit. Knows nothing about the robot, so it drops into any project.",
      tools: ["Python", "OpenCV", "RTSP", "ONVIF"],
      controls: [
        "probe.py diagnoses the connection before OpenCV gets involved",
        "serve.py re-streams to a browser — no Python needed to watch",
        "Credentials and IPs come from the CAAD lab administrator, never the repo",
      ],
      path: "Projects/Tapo_Camera_Access/",
      file: "tapocam.py",
      ticks: ["RTSP", "MULTI-CAM", "HTTP RELAY"],
    },
    {
      id: "robo-lab-model",
      number: "09",
      title: "Robo Lab 3D Model",
      subtitle: "Digital twin of the cell",
      tag: "Reference",
      tagClass: "tag-navy",
      summary:
        "Up-to-date Rhino model of the robot cell and Room 4 layout. Use it for collision checks, planning, and to drop new fixtures into context before fabricating.",
      tools: ["Rhino", "Grasshopper"],
      controls: [
        "Robo_Lab.3dm — main lab cell model",
        "room4fix.3dm — corrected room geometry",
        "storage-BOX.gh — parametric storage definition",
      ],
      path: "Projects/Robo_lab_Model/",
      ticks: ["RHINO 7", "DIGITAL TWIN"],
    },
  ],

  /* --------------------------- HARDWARE --------------------- */
  hardware: [
    {
      id: "ur10e-arm",
      name: "Universal Robots UR10e",
      category: "Robot",
      summary:
        "Six-axis collaborative robot arm. 10 kg payload, 1300 mm reach. Programmed via Teach Pendant (PolyScope) or remotely over RTDE / Modbus / Profinet.",
      specs: {
        Payload: "10 kg",
        Reach: "1300 mm",
        Joints: "6 rotary",
        Repeat: "± 0.05 mm",
        IO: "Tool flange M8 8-pin",
        Power: "12V / 24V @ 2A (tool)",
      },
    },
    {
      id: "ur10e-controlbox",
      name: "UR Control Box",
      category: "Robot",
      summary:
        "The robot's compute and power unit. Houses the safety controller, IO board, and the network interface used for remote control.",
      specs: {
        Network: "Ethernet (static IP)",
        Modes: "Local · Remote",
        IO: "16× DI / 16× DO / 4× AI",
        Power: "100–240 V AC",
      },
    },
    {
      id: "teach-pendant",
      name: "UR Teach Pendant",
      category: "Robot",
      summary:
        "12-inch touchscreen for jogging, scripting (URScript), and switching between Local and Remote Control. Houses the red Emergency Stop button.",
      specs: {
        Software: "PolyScope",
        Modes: "Local · Remote",
        Safety: "Hardware E-Stop",
      },
    },
    {
      id: "tapo-c110",
      name: "TP-Link Tapo C110",
      category: "Camera",
      summary:
        "Wi-Fi indoor camera used as the lab's overhead vision sensor. RTSP-accessible; pairs with AprilTag for world-coordinate calibration.",
      specs: {
        Resolution: "3 MP (2304 × 1296)",
        FOV: "~115°",
        Stream: "RTSP / ONVIF",
        Mount: "Tripod or wall",
      },
    },
    {
      id: "pi-zero",
      name: "Raspberry Pi Zero 2 W",
      category: "Compute",
      summary:
        "Compact Linux board used as the on-arm sensor / actuator node. Runs a thin Flask/FastAPI service exposing camera snapshots to the workstation.",
      specs: {
        CPU: "Quad-core Cortex-A53 @ 1 GHz",
        RAM: "512 MB",
        Wireless: "2.4 GHz Wi-Fi + BT",
        OS: "Raspberry Pi OS Lite",
      },
    },
    {
      id: "ai-camera-imx500",
      name: "Raspberry Pi AI Camera (IMX500)",
      category: "Camera",
      summary:
        "Sony IMX500 sensor with on-sensor neural-network inference. Used wrist-mounted on the UR10e for keyframe capture and lightweight on-device pre-processing.",
      specs: {
        Sensor: "Sony IMX500 (12 MP)",
        Inference: "On-sensor NPU",
        Interface: "CSI / MIPI",
      },
    },
    {
      id: "lab-network",
      name: "Lab Network (robot-wifi)",
      category: "Network",
      summary:
        "Isolated lab Wi-Fi for robot control. All hosts must be on this network for ur_rtde to reach the controller.",
      specs: {
        SSID: "robot-wifi",
        Password: "See router label",
        "UR10e IP": "192.168.x.x (Teach Pendant → About)",
      },
    },
  ],

  /* --------------------------- SAFETY RULES ----------------- */
  safety: [
    {
      title: "Emergency Stop",
      icon: "!",
      level: "danger",
      body: "Locate the red E-Stop button on the Teach Pendant before every run. Anyone in the room may press it. If pressed, do not reset until the cause is understood.",
    },
    {
      title: "Remote Control Mode",
      icon: "R",
      level: "warn",
      body: "To drive the robot from Python (ur_rtde), the Teach Pendant must be in Remote Control mode. Local jogging is disabled while remote is active.",
    },
    {
      title: "Clear the Reach Zone",
      icon: "◎",
      level: "warn",
      body: "Keep people and expensive equipment out of the ~1.3 m reach radius. The cobot is force-limited but not magic — moving parts still hurt.",
    },
    {
      title: "Slow First, Always",
      icon: "%",
      level: "note",
      body: "Test new code with the Teach Pendant speed slider at 10 % or lower. Raise it only after the move is verified end-to-end.",
    },
    {
      title: "Tool & Cabling",
      icon: "T",
      level: "note",
      body: "Confirm end-effector is mounted, payload is set correctly in PolyScope, and tool cables are routed so they cannot snag during motion.",
    },
    {
      title: "Network Hygiene",
      icon: "N",
      level: "note",
      body: "Stay on robot-wifi. Never commit IPs, passwords, or auth tokens to the GitHub repo — use placeholders like YOUR_IP and a local .env.",
    },
  ],

  /* --------------------------- CONTACT ---------------------- */
  // Robot-use requests are addressed to `to`, with `cc` copied in.
  // Change these two lines to redirect where requests land.
  contact: {
    to: "hrithik.shetty@th-owl.de",
    cc: "hans.sachs@th-owl.de",
    subjectPrefix: "Robot Lab Request",
    people: [
      {
        id: "hans-sachs",
        name: "Prof. Hans Sachs",
        role: "Head of Department — CAAD",
        email: "hans.sachs@th-owl.de",
      },
      {
        id: "hrithik-shetty",
        name: "Hrithik Shetty",
        role: "Teaching Assistant — CAAD",
        email: "hrithik.shetty@th-owl.de",
      },
    ],
  },
};
