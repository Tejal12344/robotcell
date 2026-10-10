# Mini Robot Cell Operator Console

## Run
```bash
docker compose up --build
```
Open: http://localhost:8080

## Stack
- ROS 2 Jazzy
- rosbridge_websocket
- robot_state_publisher
- Hand-written 6-DOF revolute URDF
- React main console
- Vue camera/pick panel
- Python ROS backend + OpenCV camera fallback
- nginx serves the browser UI

## Camera
The compose service uses privileged mode so `/dev/video0` can be visible when present without making the compose file fail when it is absent. If no camera is available, the backend logs a warning and generates a 1280x720 synthetic image.

## What works / What doesn't / What I'd do next
Update this section after testing. Do not claim features that have not been tested.

## Verification
- E-STOP: press E-STOP, move a slider, and check backend log for `joint command rejected`.
- No-camera fallback: run on a machine with no `/dev/video0`; the UI should still show the synthetic camera.
- Reconnect: stop/restart the backend process/container and confirm the indicator returns to green.

## Image size and cold build
Fill these in after running `docker images` and timing `docker compose build`.

## Bonuses
None attempted until all mandatory requirements are stable.
