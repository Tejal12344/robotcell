#!/bin/bash

set -e

echo "======================================"
echo " Mini Robot Cell Operator Console"
echo "======================================"

source /opt/ros/jazzy/setup.bash


echo "[1/4] Starting rosbridge..."

ros2 run rosbridge_server rosbridge_websocket \
  --ros-args \
  -p port:=9090 \
  > /tmp/rosbridge.log 2>&1 &


echo "[2/4] Starting robot_state_publisher..."

python3 /app/backend/launch/rsp_launch.py \
  > /tmp/rsp.log 2>&1 &


echo "[3/4] Starting robot backend..."

python3 /app/backend/nodes/cell_backend.py \
  > /tmp/backend.log 2>&1 &


echo "[4/4] Waiting for backend..."

for i in {1..20}
do
    if curl -s http://127.0.0.1:5000/health > /dev/null
    then
        break
    fi

    sleep 0.5
done


echo ""
echo "======================================"
echo " Web UI: http://localhost:8080"
echo "======================================"
echo ""

nginx -g 'daemon off;'