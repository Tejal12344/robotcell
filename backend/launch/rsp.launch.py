from pathlib import Path

from launch import LaunchDescription, LaunchService
from launch_ros.actions import Node


def generate_launch_description():

    urdf_path = Path(
        "/app/backend/urdf/mini_robot.urdf"
    )

    urdf = urdf_path.read_text()

    return LaunchDescription([

        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",

            name="robot_state_publisher",

            parameters=[
                {
                    "robot_description": urdf
                }
            ],

            output="screen"
        )

    ])


if __name__ == "__main__":

    service = LaunchService()

    service.include_launch_description(
        generate_launch_description()
    )

    service.run()