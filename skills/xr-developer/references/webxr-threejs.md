# WebXR with Three.js

## Session Setup

Initialize a WebXR session with controller and hand tracking support. This example sets up a VR scene with both controller models and hand input.

```js
import * as THREE from "three";
import { VRButton } from "three/addons/webxr/VRButton.js";
import { XRControllerModelFactory } from "three/addons/webxr/XRControllerModelFactory.js";

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.xr.enabled = true;
document.body.appendChild(VRButton.createButton(renderer));

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 100);

// Controller setup with model loading
const controllerModelFactory = new XRControllerModelFactory();
for (let i = 0; i < 2; i++) {
  const controller = renderer.xr.getController(i);
  scene.add(controller);
  const grip = renderer.xr.getControllerGrip(i);
  grip.add(controllerModelFactory.createControllerModel(grip));
  scene.add(grip);
  controller.addEventListener("selectstart", onSelect);
}

// Handler for controller select events — places a small cube at the controller position
function onSelect(event) {
  const controller = event.target;
  const geometry = new THREE.BoxGeometry(0.06, 0.06, 0.06);
  const material = new THREE.MeshStandardMaterial({ color: 0x44aa88 });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(controller.position);
  mesh.quaternion.copy(controller.quaternion);
  scene.add(mesh);
}

// Hand tracking (if available)
for (let i = 0; i < 2; i++) {
  const hand = renderer.xr.getHand(i);
  scene.add(hand);
}

renderer.setAnimationLoop((time, frame) => {
  if (frame) {
    const session = renderer.xr.getSession();
    for (const source of session.inputSources) {
      if (source.hand) handleHandInput(source, frame);
      else if (source.gamepad) handleControllerInput(source, frame);
    }
  }
  renderer.render(scene, camera);
});
```

## Input Handling

### Hand Tracking (Pinch Detection)

Detect pinch gestures by measuring the distance between thumb tip and index finger tip. When the distance falls below a threshold (0.02m), a pinch is detected.

```js
// Process hand tracking input — detect pinch gesture between thumb and index finger
function handleHandInput(source, frame) {
  const hand = source.hand;
  const refSpace = renderer.xr.getReferenceSpace();
  const indexTip = hand.get("index-finger-tip");
  const thumbTip = hand.get("thumb-tip");
  if (indexTip && thumbTip) {
    const indexPose = frame.getJointPose(indexTip, refSpace);
    const thumbPose = frame.getJointPose(thumbTip, refSpace);
    if (indexPose && thumbPose) {
      const distance = new THREE.Vector3()
        .copy(indexPose.transform.position)
        .distanceTo(new THREE.Vector3().copy(thumbPose.transform.position));
      if (distance < 0.02) {
        // Pinch detected — trigger select at midpoint
        const midpoint = new THREE.Vector3()
          .copy(indexPose.transform.position)
          .lerp(new THREE.Vector3().copy(thumbPose.transform.position), 0.5);
        console.log("Pinch at", midpoint);
      }
    }
  }
}
```

### Controller Input (Trigger + Thumbstick)

Read trigger values and thumbstick axes from the XRInputSource gamepad.

```js
// Process controller input — read trigger value and thumbstick axes
function handleControllerInput(source, frame) {
  const gamepad = source.gamepad;
  const triggerValue = gamepad.buttons[0]?.value ?? 0;
  const thumbstickX = gamepad.axes[2] ?? 0;
  const thumbstickY = gamepad.axes[3] ?? 0;
  if (triggerValue > 0.5) {
    console.log("Trigger pressed", { triggerValue, thumbstickX, thumbstickY });
  }
}
```

### Input Fallback Chain

Design input handling with a fallback chain to support multiple devices:
1. **Hand tracking** (Vision Pro, Quest with hand tracking enabled)
2. **Controllers** (Quest, WMR headsets)
3. **Gaze + dwell** (fallback when neither is available)

Always check via `XRInputSource` -- never assume hand tracking or controller availability.
