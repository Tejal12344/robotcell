# # Stage 1: build both React and Vue front ends.
# FROM node:22-bookworm AS frontend-build
# WORKDIR /src
# COPY frontend/react-app/package*.json ./react-app/
# COPY frontend/vue-panel/package*.json ./vue-panel/
# RUN cd react-app && npm install
# RUN cd ../vue-panel && npm install
# COPY frontend/react-app ./react-app
# COPY frontend/vue-panel ./vue-panel
# RUN cd vue-panel && npm run build
# RUN cp /src/vue-panel/dist/vue-panel.iife.js /src/react-app/public/vue-panel.js
# RUN cd /src/react-app && npm run build

# # Runtime: ROS 2 + Python + nginx.
# FROM ros:jazzy-ros-base
# ENV DEBIAN_FRONTEND=noninteractive
# RUN apt-get update && apt-get install -y --no-install-recommends     ros-jazzy-rosbridge-server     ros-jazzy-robot-state-publisher     python3-opencv python3-yaml nginx     && rm -rf /var/lib/apt/lists/*

# WORKDIR /opt/robot
# COPY --from=frontend-build /src/react-app/dist /var/www/robot-console
# COPY --from=frontend-build /src/vue-panel/dist /opt/robot/vue-panel
# COPY backend/urdf /opt/robot/urdf
# COPY backend/nodes /opt/robot/nodes
# COPY backend/launch /opt/robot/launch
# COPY backend/nginx.conf /etc/nginx/sites-available/default
# COPY config/cell.yaml /opt/robot/config/cell.yaml
# COPY backend/start.sh /opt/robot/start.sh
# RUN chmod +x /opt/robot/start.sh

# EXPOSE 8080 9090
# ENTRYPOINT ["/opt/robot/start.sh"]



# =========================================================
# STAGE 1 - BUILD VUE
# =========================================================

FROM node:22-alpine AS vue-build

WORKDIR /src/vue-panel

COPY frontend/vue-panel/package.json ./

RUN npm install

COPY frontend/vue-panel/ ./

RUN npm run build


# =========================================================
# STAGE 2 - BUILD REACT
# =========================================================

FROM node:22-alpine AS react-build

WORKDIR /src/react-app

COPY frontend/react-app/package.json ./

RUN npm install

COPY frontend/react-app/ ./

# Copy Vue production bundle into React public folder
COPY --from=vue-build /src/vue-panel/dist/vue-panel.js ./public/vue-panel.js
# Copy URDF into React public folder
COPY backend/urdf/mini_robot.urdf ./public/mini_robot.urdf

RUN npm run build


# =========================================================
# STAGE 3 - ROS2 RUNTIME
# =========================================================

FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    python3-flask \
    python3-opencv \
    python3-numpy \
    ros-jazzy-rosbridge-server \
    ros-jazzy-robot-state-publisher \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


# React production files

COPY --from=react-build \
    /src/react-app/dist \
    /usr/share/nginx/html


# Backend files

COPY backend/urdf /app/backend/urdf

COPY backend/nodes /app/backend/nodes

COPY backend/launch /app/backend/launch


# Nginx

COPY backend/nginx.conf \
    /etc/nginx/sites-available/default


# Start script

COPY backend/start.sh /app/start.sh

RUN chmod +x /app/start.sh


EXPOSE 8080


CMD ["/app/start.sh"]