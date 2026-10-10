import React, {
    useEffect,
    useRef,
    useState
} from "react";

import {
    createRoot
} from "react-dom/client";

import * as THREE from "three";

import URDFLoader from "urdf-loader";

import * as ROSLIB from "roslib";
import "./style.css";


const JOINTS = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6"
];


const LIMITS = {

    joint_1: [
        -Math.PI,
        Math.PI
    ],

    joint_2: [
        -2.5,
        2.5
    ],

    joint_3: [
        -2.5,
        2.5
    ],

    joint_4: [
        -Math.PI,
        Math.PI
    ],

    joint_5: [
        -2,
        2
    ],

    joint_6: [
        -Math.PI,
        Math.PI
    ]

};


const HOME = [
    0,
    -0.8,
    1,
    0,
    0.6,
    0
];


const websocketURL =
    `ws://${window.location.host}/rosbridge`;


// ========================================================
// 3D ROBOT
// ========================================================

function RobotViewer({
    joints
}) {

    const mount =
        useRef(null);

    const robotRef =
        useRef(null);


    useEffect(() => {

        const scene =
            new THREE.Scene();


        scene.background =
            new THREE.Color(
                0xf3f4f6
            );


        const camera =
            new THREE.PerspectiveCamera(
                45,
                1,
                0.01,
                100
            );


        camera.position.set(
            2.8,
            2.2,
            2.8
        );


        camera.lookAt(
            0,
            0,
            0.7
        );


        const renderer =
            new THREE.WebGLRenderer({
                antialias: true
            });


        renderer.setPixelRatio(
            window.devicePixelRatio
        );


        mount.current.appendChild(
            renderer.domElement
        );


        const light =
            new THREE.HemisphereLight(
                0xffffff,
                0x555555,
                2
            );


        scene.add(light);


        const grid =
            new THREE.GridHelper(
                4,
                20
            );


        scene.add(grid);


        const loader =
            new URDFLoader();


        loader.load(
            "/mini_robot.urdf",
            (robot) => {

                robotRef.current =
                    robot;

                scene.add(robot);

            }
        );


        let animationFrame;


        function resize() {

            if (!mount.current) {
                return;
            }


            const width =
                mount.current.clientWidth;


            const height =
                mount.current.clientHeight;


            camera.aspect =
                width / height;


            camera.updateProjectionMatrix();


            renderer.setSize(
                width,
                height
            );

        }


        resize();


        window.addEventListener(
            "resize",
            resize
        );


        function animate() {

            animationFrame =
                requestAnimationFrame(
                    animate
                );


            renderer.render(
                scene,
                camera
            );

        }


        animate();


        return () => {

            cancelAnimationFrame(
                animationFrame
            );


            window.removeEventListener(
                "resize",
                resize
            );


            renderer.dispose();


            if (
                mount.current &&
                renderer.domElement.parentNode
            ) {

                mount.current.removeChild(
                    renderer.domElement
                );

            }

        };

    }, []);


    useEffect(() => {

        const robot =
            robotRef.current;


        if (!robot) {
            return;
        }


        JOINTS.forEach(
            (jointName) => {

                try {

                    robot.setJointValue(
                        jointName,
                        joints[jointName] ?? 0
                    );

                } catch (error) {

                    console.warn(
                        "Joint update failed:",
                        jointName
                    );

                }

            }
        );

    }, [joints]);


    return (

        <div
            className="viewer"
            ref={mount}
        />

    );

}


// ========================================================
// MAIN REACT APP
// ========================================================

function App() {

    const [joints, setJoints] =
        useState(
            Object.fromEntries(
                JOINTS.map(
                    joint => [
                        joint,
                        0
                    ]
                )
            )
        );


    const [connected, setConnected] =
        useState(false);


    const [estop, setEstop] =
        useState(false);


    const [commandPublisher, setCommandPublisher] =
        useState(null);


    const estopRef =
        useRef(false);


    // ====================================================
    // ROS CONNECTION
    // ====================================================

    useEffect(() => {

        let active = true;

        let ros;


        function connect() {

            ros =
                new ROSLIB.Ros({
                    url: websocketURL
                });


            ros.on(
                "connection",
                () => {

                    if (!active) {
                        return;
                    }


                    setConnected(
                        true
                    );


                    // Joint states

                    const stateSubscriber =
                        new ROSLIB.Topic({

                            ros,

                            name:
                                "/joint_states",

                            messageType:
                                "sensor_msgs/JointState"

                        });


                    stateSubscriber.subscribe(
                        message => {

                            const next = {};


                            message.name.forEach(
                                (
                                    name,
                                    index
                                ) => {

                                    next[name] =
                                        message.position[
                                            index
                                        ];

                                }
                            );


                            setJoints(
                                previous => ({
                                    ...previous,
                                    ...next
                                })
                            );

                        }
                    );


                    // E-STOP state

                    const estopSubscriber =
                        new ROSLIB.Topic({

                            ros,

                            name:
                                "/estop",

                            messageType:
                                "std_msgs/Bool"

                        });


                    estopSubscriber.subscribe(
                        message => {

                            estopRef.current =
                                message.data;


                            setEstop(
                                message.data
                            );

                        }
                    );


                    // Joint command publisher

                    const publisher =
                        new ROSLIB.Topic({

                            ros,

                            name:
                                "/joint_command",

                            messageType:
                                "std_msgs/Float64MultiArray"

                        });


                    setCommandPublisher(
                        publisher
                    );

                }
            );


            ros.on(
                "close",
                () => {

                    if (!active) {
                        return;
                    }


                    setConnected(
                        false
                    );


                    setCommandPublisher(
                        null
                    );


                    setTimeout(
                        connect,
                        1000
                    );

                }
            );


            ros.on(
                "error",
                () => {

                    setConnected(
                        false
                    );

                }
            );

        }


        connect();


        return () => {

            active = false;

            if (ros) {
                ros.close();
            }

        };

    }, []);


    // ====================================================
    // SEND JOINT COMMAND
    // ====================================================

    function sendJointCommand(
        values
    ) {

        if (
            !commandPublisher ||
            estopRef.current
        ) {

            return;

        }


        const positions =
            JOINTS.map(
                joint =>
                    values[joint]
            );


        commandPublisher.publish(

            new ROSLIB.Message({

                data:
                    positions

            })

        );

    }


    // ====================================================
    // SLIDER
    // ====================================================

    function handleJointChange(
        joint,
        value
    ) {

        const next = {

            ...joints,

            [joint]:
                Number(value)

        };


        setJoints(
            next
        );


        sendJointCommand(
            next
        );

    }


    // ====================================================
    // E-STOP
    // ====================================================

    function setEstopValue(
        value
    ) {

        if (!commandPublisher) {
            // We can still publish using a
            // temporary ROS connection below.
        }


        const ros =
            new ROSLIB.Ros({
                url: websocketURL
            });


        ros.on(
            "connection",
            () => {

                const publisher =
                    new ROSLIB.Topic({

                        ros,

                        name:
                            "/estop",

                        messageType:
                            "std_msgs/Bool"

                    });


                publisher.publish(

                    new ROSLIB.Message({
                        data: value
                    })

                );


                setTimeout(
                    () => ros.close(),
                    100
                );

            }
        );

    }


    // ====================================================
    // HOME
    // ====================================================

    function home() {

        if (
            estopRef.current
        ) {

            return;

        }


        const homePose =
            Object.fromEntries(

                JOINTS.map(
                    (
                        joint,
                        index
                    ) => [

                        joint,
                        HOME[index]

                    ]
                )

            );


        sendJointCommand(
            homePose
        );

    }


    // ====================================================
    // MOUNT VUE
    // ====================================================

    useEffect(() => {

        const container =
            document.getElementById(
                "vue-panel"
            );


        if (
            container &&
            window.mountVuePanel
        ) {

           
async function mountVuePanel(element) {
  try {
    const vueModule = await import("/vue-panel.js");

    if (typeof vueModule.default === "function") {
      vueModule.default(element);
    } else if (typeof window.mountVuePanel === "function") {
      window.mountVuePanel(element);
    } else {
      console.error("Vue panel mount function was not found.");
    }
  } catch (error) {
    console.error("Failed to load Vue panel:", error);
  }
}


        }

    }, []);


    return (

        <div className="page">

            <header>

                <div>

                    <h1>
                        Mini Robot Cell Operator Console
                    </h1>


                    <span
                        className={
                            connected
                                ? "status green"
                                : "status red"
                        }
                    >

                        ●{" "}

                        {
                            connected
                                ? "Connected"
                                : "Disconnected"
                        }

                    </span>


                    <span className="url">

                        {websocketURL}

                    </span>

                </div>


                <div className="buttons">

                    <button
                        onClick={home}
                        disabled={estop}
                    >
                        HOME
                    </button>


                    <button
                        className="danger"
                        onClick={() =>
                            setEstopValue(true)
                        }
                    >
                        E-STOP
                    </button>


                    <button
                        onClick={() =>
                            setEstopValue(false)
                        }
                    >
                        RESET
                    </button>

                </div>

            </header>


            {
                estop && (

                    <div className="banner">

                        E-STOP LATCHED —
                        joint commands are blocked
                        by the backend.

                    </div>

                )
            }


            <main>

                {/* ===================================== */}
                {/* REACT */}
                {/* ===================================== */}

                <section className="panel">

                    <h2>
                        React — Main Console
                    </h2>


                    <RobotViewer
                        joints={joints}
                    />


                    <div className="sliders">

                        {
                            JOINTS.map(
                                joint => (

                                    <div
                                        className="joint"
                                        key={joint}
                                    >

                                        <label>

                                            {joint}

                                            <span>

                                                {
                                                    (
                                                        joints[joint] *
                                                        180 /
                                                        Math.PI
                                                    ).toFixed(1)
                                                }

                                                ° /

                                                {" "}

                                                {
                                                    joints[joint]
                                                        .toFixed(3)
                                                }

                                                {" "}rad

                                            </span>

                                        </label>


                                        <input
                                            type="range"

                                            min={
                                                LIMITS[
                                                    joint
                                                ][0]
                                            }

                                            max={
                                                LIMITS[
                                                    joint
                                                ][1]
                                            }

                                            step="0.01"

                                            value={
                                                joints[
                                                    joint
                                                ]
                                            }

                                            disabled={
                                                estop
                                            }

                                            onChange={
                                                event =>
                                                    handleJointChange(
                                                        joint,
                                                        event.target.value
                                                    )
                                            }

                                        />

                                    </div>

                                )
                            )
                        }

                    </div>

                </section>


                {/* ===================================== */}
                {/* VUE */}
                {/* ===================================== */}

                <section className="panel">

                    <h2>
                        Vue — Camera & Pick Panel
                    </h2>


                    <div
                        id="vue-panel"
                    />

                </section>

            </main>

        </div>

    );

}


createRoot(
    document.getElementById(
        "root"
    )
).render(
    <App />
);