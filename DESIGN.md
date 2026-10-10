# DESIGN

## 1. Architecture

Browser
  React main console
    - Three.js + URDFLoader
    - joint sliders / HOME / E-STOP
    - ROSLIB WebSocket
  Vue camera/pick panel
    - MJPEG camera
    - pixel -> mm
    - latency compensation
         |
         | WebSocket / HTTP
         v
Docker container
  rosbridge_websocket :9090
  robot_state_publisher
  cell_backend.py
    - /joint_command sensor_msgs/JointState
    - /joint_states sensor_msgs/JointState
    - /estop std_msgs/Bool
    - /pick_target geometry_msgs/PointStamped
    - camera MJPEG :5000
  nginx :8080

## 2. Topics and units

/joint_command: sensor_msgs/JointState, radians
/joint_states: sensor_msgs/JointState, radians, 20 Hz
/estop: std_msgs/Bool
/pick_target: geometry_msgs/PointStamped, millimetres; frame_id=camera

## 3. React + Vue integration
React owns the main console. Vue is built as a separate application bundle and mounted into a dedicated DOM element by `window.mountVuePanel`. This keeps the legacy Vue widget tree genuinely separate while allowing the React page to host it.

Trade-off: a global mount function is simple and lightweight, but a Web Component would give stronger encapsulation.

## 4. Camera transport
The camera uses MJPEG HTTP because the UI only needs a live image and the transport is simple. ROS remains responsible for robot state and command messaging.

## 5. Pixel to millimetre maths
Let the source image be W=1280 and H=720. If the displayed image rectangle is displayW x displayH and the click is at display coordinates x,y:

u = x * (W / displayW)
v = y * (H / displayH)

With mm_per_pixel = 0.4:
dx_mm = (u - W/2) * 0.4
dy_mm = (v - H/2) * 0.4

This explicitly handles CSS/display scaling.

## 6. Latency compensation
belt_speed = 0.25 m/s
latency = 0.200 s

extra distance = 0.25 * 0.200 = 0.050 m = 50 mm

The compensation is shown as an additional +X offset.

## 7. E-STOP
The UI publishes `/estop`, but the backend also checks the latched server-side state before accepting `/joint_command`. Therefore disabling the sliders is not the safety mechanism; the backend rejection is.

## 8. Deliberate scope cuts
No Gazebo/Webots, IK, MQTT, or blob detection in the mandatory version. These are intentionally postponed until the one-command build, camera fallback, ROS topics, and UI round-trip are verified.
