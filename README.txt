================================================================================
  LOBSTER SORT — Autonomous Laundry Sorter (SO-101 Hackathon)
================================================================================

  GitHub homepage: see README.md (same content, Markdown formatting).
  This file is a plain-text copy for local reference.

================================================================================
  MAIN DEMO — watch first
================================================================================

  YouTube (full submission):
  https://www.youtube.com/shorts/__rTiI1dL4w

  Thumbnail image: Images/video_thumbnail.png

================================================================================
  WHAT IT DOES
================================================================================

  Lobster Sort uses:
    - SO-101 follower arm (pick, place)
    - Overhead USB camera (sock detection)
    - Atech.dev humidity sensor (wet vs dry)
    - Two bins (left = wet, right = dry)

  Pipeline (mainFINAL.py):
    1. detect_sock()     -> pixel (sock_x, sock_y)
    2. interpolate_pose()-> 5 joint angles
    3. close gripper     -> set_gripper_open_value(0.0)
    4. SENSOR_POSE       -> hold at sensor
    5. humidity measure  -> Wet or Dry
    6. LEFT_BIN or RIGHT_BIN -> open gripper

  Result: Hackathon winner — best use of Atech.dev systems.

================================================================================
  FOLDER MAP
================================================================================

  Images/
    LobsterSort_final_build.jpg    final robot + workspace
    default_camera_view.png        bird's-eye camera mount
    sock_object_detection_camera.png   vision overlay
    camera_error_example.png       webcam troubleshooting
    video_thumbnail.png            YouTube link thumbnail

  Videos/
    leader_follower_demo.mp4       teleop development
    dry_test1.mp4, dry_test2.mp4   dry sock tests
    wet_test.mp4                   wet sock test

  example_so101/
    so101_controller.py            follower arm driver
    environment.yaml               conda env so101-teleop
    examples/
      mainFINAL.py                 *** RUN THIS for full demo ***
      main.py                      pose-replay (no camera)
      objectDetect.py              vision-only test
      move_to_sock.py              press 'm' to move to sock
      sock_calibrate.py            calibration grid
      record_poses.py              teach poses -> poses.json
      play_poses.py                replay poses
      sensor_according_to_rate.py  sensor-only test
      poses.json                   saved joint poses
      common/configs.py            ROBOT_RATE, NEUTRAL_JOINT_ANGLES, etc.

  neuracore/                       vendored SDK (optional teleop logging)

================================================================================
  QUICK START (Windows — ZenBook 14 example ports)
================================================================================

  Leader  = COM4    Follower = COM6    Sensor = COM7    Camera = index 1

  conda activate so101-teleop
  cd example_so101\examples
  python mainFINAL.py

  Controls: Enter = start cycle    q + Enter = quit

  One-time calibration:
    lerobot-find-port
    lerobot-calibrate --teleop.type=so101_leader --teleop.port=COM4 --teleop.id=my_leader
    lerobot-calibrate --robot.type=so101_follower --robot.port=COM6 --robot.id=my_follower_arm

  Teleop test:
    python 1_leader_arm_teleop_so101.py --real-robot --leader-port COM4 --leader-id my_leader --follower-port COM6 --follower-id my_follower_arm

================================================================================
  KEY VARIABLES (mainFINAL.py)
================================================================================

  ROBOT
    PORT              COM6
    FOLLOWER_ID       my_follower_arm
    MOVE_SPEED        0.02 sec between interpolation steps
    STEP_SIZE         1.0 degree per step

  SENSOR (Atech JSON over serial)
    SENSOR_PORT       COM7
    BASELINE_SECONDS  10
    MEASURE_SECONDS   10
    HUM_THRESHOLD     -20     (avg rate > threshold => Wet)

  VISION (detect_sock)
    frame             640 x 480
    camera            VideoCapture(1, CAP_DSHOW), fallback 0
    threshold         80 (THRESH_BINARY_INV)
    min area          5000 pixels

  REACH CALIBRATION
    CALIBRATION       5 pixel<->pose pairs (inverse distance weights)
    HOVER_OFFSET      250     joint[1] -= , joint[2] +=
    REACH_OFFSET      250     joint[1] += , joint[2] -=

  FIXED POSES (5 joint angles each)
    SENSOR_POSE       at humidity pad
    LEFT_BIN_POSE     wet
    RIGHT_BIN_POSE    dry

  GRIPPER
    open              set_gripper_open_value(0.5)
    close             set_gripper_open_value(0.0)

  configs.py (shared)
    ROBOT_RATE        100 Hz
    NEUTRAL_JOINT_ANGLES   [0, 90, -90, 0, 0] degrees
    CAMERA_DEVICE_INDEX    1

  poses.json keys
    sensor, Lbin, Rbin, closeLow, farLow, farHigh, closeHigh, closeSense

================================================================================
  DEVELOPMENT LOG (original hackathon notes)
================================================================================

  1.  Robot setup: LeRobot repos, ports, calibration to max range.
  2.  Leader/follower teleop; motor jitter fixed by replacement.
  3.  Camera + humidity sensor mounting; bird's-eye view chosen.
  4.  Neuracore explored; uploads stalled — pivoted to on-device pipeline.
  5.  New plan: detect cloth -> move -> sense -> sort to bin.
  6.  objectDetect.py: sock vs background, centroid in camera frame.
  7.  record_poses.py / poses.json: sensor, Lbin, Rbin taught by hand.
  8.  Inverse kinematics abandoned (camera drift); weighted interpolation used.
  9.  White paper background + fixed camera improved repeatability.
  10. Gripper code, delays, HOVER_OFFSET / REACH_OFFSET / HUM_THRESHOLD tuning.
  11. Lobster Sort branding; YouTube demo; Atech.dev prize winner.

  Full polished documentation: README.md
