# #!/usr/bin/env python3
# import math, os, threading, time
# import cv2
# import yaml
# import numpy as np
# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import JointState
# from std_msgs.msg import Bool
# from geometry_msgs.msg import PointStamped
# from flask import Flask, Response

# CONFIG = "/opt/robot/config/cell.yaml"

# with open(CONFIG, "r") as f:
#     CFG = yaml.safe_load(f)

# JOINT_NAMES = [f"joint_{i}" for i in range(1, 7)]
# state = [float(x) for x in CFG["robot"]["home_pose"]]
# target = state.copy()
# estop = False
# lock = threading.Lock()

# app = Flask(__name__)
# latest_frame = None

# def synthetic_frame():
#     img = np.zeros((CFG["camera"]["height"], CFG["camera"]["width"], 3), dtype=np.uint8)
#     img[:] = (35, 35, 35)
#     t = time.time()
#     x = int(640 + 350 * math.sin(t))
#     y = int(360 + 180 * math.cos(t * 0.7))
#     cv2.line(img, (640, 0), (640, 720), (80, 80, 80), 1)
#     cv2.line(img, (0, 360), (1280, 360), (80, 80, 80), 1)
#     cv2.circle(img, (x, y), 35, (0, 180, 255), -1)
#     cv2.putText(img, "SYNTHETIC CAMERA", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
#                 (255,255,255), 2)
#     cv2.putText(img, time.strftime("%H:%M:%S"), (30, 90),
#                 cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
#     return img

# def camera_loop():
#     global latest_frame
#     device = CFG["camera"]["device"]
#     cap = cv2.VideoCapture(device)
#     real = cap.isOpened()
#     if not real:
#         print(f"[camera] WARNING: cannot open {device}; using synthetic fallback", flush=True)
#     while True:
#         if real:
#             ok, frame = cap.read()
#             if not ok:
#                 print("[camera] WARNING: camera read failed; switching to synthetic", flush=True)
#                 real = False
#                 cap.release()
#                 frame = synthetic_frame()
#         else:
#             frame = synthetic_frame()
#         ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
#         if ok:
#             latest_frame = jpg.tobytes()
#         time.sleep(1.0 / CFG["camera"]["fps"])

# @app.route("/")
# def camera():
#     def gen():
#         while True:
#             if latest_frame:
#                 yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
#                        latest_frame + b"\r\n")
#             time.sleep(1.0 / CFG["camera"]["fps"])
#     return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

# class CellNode(Node):
#     def __init__(self):
#         super().__init__("cell_backend")
#         self.pub_state = self.create_publisher(
#             JointState, CFG["ros"]["joint_states_topic"], 10)
#         self.pub_estop = self.create_publisher(
#             Bool, CFG["ros"]["estop_topic"], 10)
#         self.create_subscription(
#             JointState, CFG["ros"]["joint_command_topic"], self.command_cb, 10)
#         self.create_subscription(
#             Bool, CFG["ros"]["estop_topic"], self.estop_cb, 10)
#         self.create_subscription(
#             PointStamped, CFG["ros"]["pick_target_topic"], self.pick_cb, 10)
#         self.timer = self.create_timer(1.0 / CFG["robot"]["publish_hz"], self.tick)
#         self.get_logger().info("Cell backend ready")

#     def command_cb(self, msg):
#         global target
#         with lock:
#             if estop:
#                 self.get_logger().warn("E-STOP latched: joint command rejected")
#                 return
#             if len(msg.position) >= 6:
#                 target = list(msg.position[:6])
#                 self.get_logger().info(f"Accepted joint command: {target}")

#     def estop_cb(self, msg):
#         global estop
#         with lock:
#             estop = bool(msg.data)
#             self.get_logger().warn(f"E-STOP = {estop}")

#     def pick_cb(self, msg):
#         self.get_logger().info(
#             f"PICK TARGET: x={msg.point.x:.2f} y={msg.point.y:.2f} z={msg.point.z:.2f} mm")

#     def tick(self):
#         global state
#         max_step = CFG["robot"]["max_joint_velocity"] / CFG["robot"]["publish_hz"]
#         with lock:
#             if not estop:
#                 for i in range(6):
#                     delta = target[i] - state[i]
#                     state[i] += max(-max_step, min(max_step, delta))
#             msg = JointState()
#             msg.header.stamp = self.get_clock().now().to_msg()
#             msg.name = JOINT_NAMES
#             msg.position = state
#             self.pub_state.publish(msg)

# def ros_main():
#     rclpy.init()
#     node = CellNode()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == "__main__":
#     threading.Thread(target=camera_loop, daemon=True).start()
#     threading.Thread(target=lambda: app.run(host="127.0.0.1", port=5000, threaded=True),
#                      daemon=True).start()
#     ros_main()




#!/usr/bin/env python3

import threading
import time

import cv2
import numpy as np

from flask import Flask, Response, jsonify

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float64MultiArray
from geometry_msgs.msg import PointStamped


# =========================================================
# ROBOT CONFIGURATION
# =========================================================

JOINTS = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6"
]


HOME = np.array(
    [
        0.0,
        -0.8,
        1.0,
        0.0,
        0.6,
        0.0
    ],
    dtype=float
)


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)

backend_node = None


# =========================================================
# ROS NODE
# =========================================================

class CellBackend(Node):

    def __init__(self):

        super().__init__("cell_backend")

        # Current reported robot state
        self.state = HOME.copy()

        # Desired robot state
        self.target = HOME.copy()

        # Emergency stop state
        self.estop = False

        self.lock = threading.Lock()


        # -------------------------------------------------
        # Publishers
        # -------------------------------------------------

        self.state_pub = self.create_publisher(
            JointState,
            "/joint_states",
            10
        )

        self.estop_pub = self.create_publisher(
            Bool,
            "/estop",
            10
        )


        # -------------------------------------------------
        # Subscribers
        # -------------------------------------------------

        self.create_subscription(
            Float64MultiArray,
            "/joint_command",
            self.command_callback,
            10
        )

        self.create_subscription(
            Bool,
            "/estop",
            self.estop_callback,
            10
        )

        self.create_subscription(
            PointStamped,
            "/pick_target",
            self.pick_callback,
            10
        )


        # -------------------------------------------------
        # 20 Hz state publisher
        # -------------------------------------------------

        self.create_timer(
            0.05,
            self.publish_state
        )


        # -------------------------------------------------
        # Camera
        # -------------------------------------------------

        self.cap = cv2.VideoCapture(
            "/dev/video0"
        )

        if self.cap.isOpened():

            self.camera_ok = True

            self.get_logger().info(
                "Camera opened: /dev/video0"
            )

        else:

            self.camera_ok = False

            self.get_logger().warn(
                "Cannot open /dev/video0. "
                "Using synthetic camera fallback."
            )

            self.cap.release()


        self.frame_lock = threading.Lock()

        self.latest_frame = (
            self.make_synthetic_frame()
        )


        # Start camera thread

        camera_thread = threading.Thread(
            target=self.camera_loop,
            daemon=True
        )

        camera_thread.start()


    # =====================================================
    # E-STOP
    # =====================================================

    def estop_callback(self, msg):

        with self.lock:

            self.estop = bool(
                msg.data
            )


        self.estop_pub.publish(
            Bool(data=self.estop)
        )


        if self.estop:

            self.get_logger().warn(
                "E-STOP LATCHED"
            )

        else:

            self.get_logger().info(
                "E-STOP RESET"
            )


    # =====================================================
    # JOINT COMMAND
    # =====================================================

    def command_callback(self, msg):

        with self.lock:

            # IMPORTANT:
            # Backend enforcement of E-STOP

            if self.estop:

                self.get_logger().warn(
                    "E-STOP latched: "
                    "joint command rejected"
                )

                return


            if len(msg.data) != 6:

                self.get_logger().warn(
                    "Invalid joint command. "
                    "Expected 6 values."
                )

                return


            self.target = np.array(
                msg.data,
                dtype=float
            )


    # =====================================================
    # PICK TARGET
    # =====================================================

    def pick_callback(self, msg):

        self.get_logger().info(
            "PICK TARGET: "
            f"x={msg.point.x:.2f} mm, "
            f"y={msg.point.y:.2f} mm, "
            f"z={msg.point.z:.2f} mm"
        )


    # =====================================================
    # PUBLISH JOINT STATE
    # =====================================================

    def publish_state(self):

        with self.lock:

            if not self.estop:

                difference = (
                    self.target -
                    self.state
                )

                # Smooth movement

                step = 0.08

                self.state += np.clip(
                    difference,
                    -step,
                    step
                )


            state = self.state.copy()

            estop = self.estop


        msg = JointState()

        msg.header.stamp = (
            self.get_clock()
            .now()
            .to_msg()
        )

        msg.name = JOINTS

        msg.position = (
            state.tolist()
        )


        self.state_pub.publish(
            msg
        )


        self.estop_pub.publish(
            Bool(data=estop)
        )


    # =====================================================
    # SYNTHETIC IMAGE
    # =====================================================

    def make_synthetic_frame(self):

        frame = np.zeros(
            (720, 1280, 3),
            dtype=np.uint8
        )

        frame[:] = (
            35,
            35,
            35
        )


        # Grid

        for x in range(
            0,
            1280,
            80
        ):

            cv2.line(
                frame,
                (x, 0),
                (x, 720),
                (70, 70, 70),
                1
            )


        for y in range(
            0,
            720,
            80
        ):

            cv2.line(
                frame,
                (0, y),
                (1280, y),
                (70, 70, 70),
                1
            )


        return frame


    # =====================================================
    # CAMERA LOOP
    # =====================================================

    def camera_loop(self):

        tick = 0


        while rclpy.ok():

            # ---------------------------------------------
            # REAL CAMERA
            # ---------------------------------------------

            if self.camera_ok:

                success, frame = (
                    self.cap.read()
                )


                if not success:

                    self.camera_ok = False

                    self.get_logger().warn(
                        "Camera read failed. "
                        "Switching to synthetic fallback."
                    )

                    frame = (
                        self.make_synthetic_frame()
                    )


            # ---------------------------------------------
            # SYNTHETIC CAMERA
            # ---------------------------------------------

            else:

                frame = (
                    self.make_synthetic_frame()
                )


                x = (
                    640 +
                    int(
                        250 *
                        np.sin(
                            tick / 12.0
                        )
                    )
                )


                y = (
                    360 +
                    int(
                        150 *
                        np.cos(
                            tick / 15.0
                        )
                    )
                )


                cv2.circle(
                    frame,
                    (x, y),
                    35,
                    (0, 140, 255),
                    -1
                )


                cv2.putText(
                    frame,
                    "SYNTHETIC CAMERA",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2
                )


                cv2.putText(
                    frame,
                    time.strftime(
                        "%H:%M:%S"
                    ),
                    (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2
                )


                tick += 1


            # Store latest frame

            with self.frame_lock:

                self.latest_frame = frame


            # 5 FPS

            time.sleep(0.2)


# =========================================================
# MJPEG CAMERA STREAM
# =========================================================

def mjpeg_generator():

    while True:

        with backend_node.frame_lock:

            frame = (
                backend_node
                .latest_frame
                .copy()
            )


        success, encoded = (
            cv2.imencode(
                ".jpg",
                frame,
                [
                    int(
                        cv2.IMWRITE_JPEG_QUALITY
                    ),
                    80
                ]
            )
        )


        if success:

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"\r\n"
                +
                encoded.tobytes()
                +
                b"\r\n"
            )


        time.sleep(0.2)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return jsonify(
        ok=True
    )


# =========================================================
# CAMERA ENDPOINT
# =========================================================

@app.get("/camera.mjpg")
def camera():

    return Response(
        mjpeg_generator(),
        mimetype=(
            "multipart/"
            "x-mixed-replace; "
            "boundary=frame"
        )
    )


# =========================================================
# MAIN
# =========================================================

def main():

    global backend_node


    rclpy.init()


    backend_node = (
        CellBackend()
    )


    executor = (
        rclpy.executors
        .MultiThreadedExecutor()
    )


    executor.add_node(
        backend_node
    )


    flask_thread = threading.Thread(

        target=lambda:
            app.run(
                host="127.0.0.1",
                port=5000,
                threaded=True,
                use_reloader=False
            ),

        daemon=True
    )


    flask_thread.start()


    try:

        executor.spin()

    finally:

        backend_node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":

    main()