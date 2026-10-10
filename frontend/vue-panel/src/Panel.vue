
<template>
  <div class="pick-panel">
    <div class="panel-status">
      <span class="status-dot"></span>
      Camera & Pick Control
      <span class="status-text">{{ rosConnected ? "ROS Connected" : "Connecting..." }}</span>
    </div>

    <div class="camera-container">
      <img
        ref="image"
        :src="cameraUrl"
        alt="Robot cell camera feed"
        class="camera-feed"
        @click="selectTarget"
        @load="cameraLoaded = true"
        @error="cameraLoaded = false"
      />

      <div class="camera-overlay">
        <span class="camera-label">
          {{ cameraLoaded ? "LIVE CAMERA / SIMULATED FEED" : "CONNECTING TO CAMERA..." }}
        </span>
        <span class="crosshair">+</span>
        <span class="camera-help">Click anywhere on the image to select a pick target</span>
      </div>
    </div>

    <div class="section-title">Selected Pick Target</div>

    <div class="coordinate-grid">
      <div class="coordinate-card">
        <span>Pixel X</span>
        <strong>{{ target.pixelX }}</strong>
      </div>
      <div class="coordinate-card">
        <span>Pixel Y</span>
        <strong>{{ target.pixelY }}</strong>
      </div>
      <div class="coordinate-card">
        <span>World X</span>
        <strong>{{ target.worldX.toFixed(2) }} mm</strong>
      </div>
      <div class="coordinate-card">
        <span>World Y</span>
        <strong>{{ target.worldY.toFixed(2) }} mm</strong>
      </div>
    </div>

    <div class="section-title">Conveyor Compensation</div>

    <div class="settings-grid">
      <label>
        Scale (mm/pixel)
        <input v-model.number="mmPerPixel" type="number" min="0.01" step="0.05" />
      </label>

      <label>
        Belt speed (m/s)
        <input v-model.number="beltSpeed" type="number" min="0" step="0.05" />
      </label>

      <label>
        Pipeline latency (ms)
        <input v-model.number="latencyMs" type="number" min="0" step="10" />
      </label>
    </div>

    <div class="compensation-card">
      <div>
        <span>Compensation distance</span>
        <strong>{{ compensationMm.toFixed(2) }} mm</strong>
      </div>
      <div>
        <span>Estimated travel time</span>
        <strong>{{ (latencyMs / 1000).toFixed(2) }} s</strong>
      </div>
    </div>

    <div class="target-summary">
      <strong>Command preview</strong>
      <p>X: {{ compensatedX.toFixed(2) }} mm</p>
      <p>Y: {{ target.worldY.toFixed(2) }} mm</p>
      <p class="message">{{ message }}</p>
    </div>

    <div class="button-row">
      <button class="send-button" @click="sendPickTarget" :disabled="!rosConnected">
        SEND PICK TARGET
      </button>
      <button class="clear-button" @click="clearTarget">
        CLEAR TARGET
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import * as ROSLIB from "roslib";

const image = ref(null);
const cameraLoaded = ref(false);
const rosConnected = ref(false);

const cameraUrl = `${window.location.origin}/camera.mjpg`;

const mmPerPixel = ref(0.4);
const beltSpeed = ref(0.25);
const latencyMs = ref(200);

const target = ref({
  pixelX: 0,
  pixelY: 0,
  worldX: 0,
  worldY: 0
});

const hasTarget = ref(false);
const message = ref("Click the camera image to select a target.");

let ros = null;
let pickTopic = null;

const compensationMm = computed(() => {
  return beltSpeed.value * (latencyMs.value / 1000) * 1000;
});

const compensatedX = computed(() => {
  return target.value.worldX + compensationMm.value;
});

function connectRos() {
  ros = new ROSLIB.Ros({
    url: `ws://${window.location.host}/rosbridge`
  });

  ros.on("connection", () => {
    rosConnected.value = true;
    message.value = "Connected to ROS. Select a target.";
    pickTopic = new ROSLIB.Topic({
      ros,
      name: "/pick_target",
      messageType: "geometry_msgs/msg/Point"
    });
  });

  ros.on("error", (error) => {
    console.error("Vue panel ROS error:", error);
    rosConnected.value = false;
    message.value = "ROS connection error.";
  });

  ros.on("close", () => {
    rosConnected.value = false;
    pickTopic = null;
    message.value = "ROS disconnected.";
  });
}

function selectTarget(event) {
  const bounds = event.currentTarget.getBoundingClientRect();

  const displayedX = event.clientX - bounds.left;
  const displayedY = event.clientY - bounds.top;

  // Scale click coordinates to the actual image dimensions.
  const scaleX = event.currentTarget.naturalWidth / bounds.width;
  const scaleY = event.currentTarget.naturalHeight / bounds.height;

  const pixelX = Math.round(displayedX * scaleX);
  const pixelY = Math.round(displayedY * scaleY);

  // Use the center of the image as the coordinate origin.
  const centerX = event.currentTarget.naturalWidth / 2;
  const centerY = event.currentTarget.naturalHeight / 2;

  target.value = {
    pixelX,
    pixelY,
    worldX: (pixelX - centerX) * mmPerPixel.value,
    worldY: (centerY - pixelY) * mmPerPixel.value
  };

  hasTarget.value = true;
  message.value = "Target selected. Review compensation, then send.";
}

function sendPickTarget() {
  if (!rosConnected.value || !pickTopic) {
    message.value = "ROS is not connected.";
    return;
  }

  if (!hasTarget.value) {
    message.value = "Select a point on the camera image first.";
    return;
  }

  const point = new ROSLIB.Message({
    x: compensatedX.value / 1000,
    y: target.value.worldY / 1000,
    z: 0
  });

  pickTopic.publish(point);
  message.value = "Pick target published to /pick_target.";
}

function clearTarget() {
  hasTarget.value = false;
  target.value = {
    pixelX: 0,
    pixelY: 0,
    worldX: 0,
    worldY: 0
  };
  message.value = "Target cleared. Click the image to select another.";
}

onMounted(() => {
  connectRos();
});

onBeforeUnmount(() => {
  if (ros) {
    ros.close();
  }
});
</script>

<style scoped>
.pick-panel {
  color: #172033;
  font-family: Arial, sans-serif;
}

.panel-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  font-weight: 700;
}

.status-dot {
  width: 9px;
  height: 9px;
  background: #22c55e;
  border-radius: 50%;
}

.status-text {
  margin-left: auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
}

.camera-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: #111827;
  border-radius: 10px;
}

.camera-feed {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  cursor: crosshair;
}

.camera-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.camera-label {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 6px 9px;
  border-radius: 5px;
  background: rgb(15 23 42 / 80%);
  color: white;
  font-size: 10px;
}

.crosshair {
  position: absolute;
  left: 50%;
  top: 50%;
  color: #ef4444;
  font-size: 32px;
  font-weight: bold;
  transform: translate(-50%, -50%);
}

.camera-help {
  position: absolute;
  bottom: 10px;
  left: 10px;
  right: 10px;
  color: white;
  font-size: 11px;
  text-shadow: 0 1px 4px black;
}

.section-title {
  margin: 20px 0 10px;
  font-size: 15px;
  font-weight: 700;
}

.coordinate-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.coordinate-card {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.coordinate-card span,
.compensation-card span {
  display: block;
  margin-bottom: 5px;
  color: #64748b;
  font-size: 12px;
}

.coordinate-card strong,
.compensation-card strong {
  font-size: 16px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.settings-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #475569;
}

.settings-grid input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 9px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 14px;
}

.compensation-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
  padding: 14px;
  border-radius: 8px;
  background: #eff6ff;
}

.target-summary {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.target-summary p {
  margin: 7px 0;
  font-size: 13px;
}

.target-summary .message {
  color: #475569;
  overflow-wrap: anywhere;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.button-row button {
  flex: 1;
  min-width: 120px;
  padding: 12px;
  border: none;
  border-radius: 7px;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.send-button {
  background: #2563eb;
}

.send-button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.clear-button {
  background: #475569;
}

@media (max-width: 600px) {
  .settings-grid,
  .compensation-card {
    grid-template-columns: 1fr;
  }
}
</style>
