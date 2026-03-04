# Spatial UI with A-Frame

Build floating panels, HUDs, and menus in 3D space. Place UI within ergonomic comfort zones (arm's reach, 15-degree vertical arc). Minimum hit target: 4cm diameter at arm's length (0.6m), approximately 3.8 degrees visual angle.

```html
<html>
<head>
  <script src="https://aframe.io/releases/1.6.0/aframe.min.js"></script>
  <script>
    AFRAME.registerComponent("spatial-panel", {
      schema: {
        title: { type: "string", default: "Panel" },
        width: { type: "number", default: 0.6 },
        height: { type: "number", default: 0.4 },
      },
      init: function () {
        const el = this.el;
        const data = this.data;

        // Background plane
        const bg = document.createElement("a-plane");
        bg.setAttribute("width", data.width);
        bg.setAttribute("height", data.height);
        bg.setAttribute("color", "#1a1a2e");
        bg.setAttribute("opacity", 0.92);
        bg.setAttribute("side", "double");
        el.appendChild(bg);

        // Title bar
        const titleBar = document.createElement("a-plane");
        titleBar.setAttribute("width", data.width);
        titleBar.setAttribute("height", 0.06);
        titleBar.setAttribute("position", `0 ${data.height / 2 - 0.03} 0.001`);
        titleBar.setAttribute("color", "#0f3460");
        el.appendChild(titleBar);

        // Title text
        const titleText = document.createElement("a-text");
        titleText.setAttribute("value", data.title);
        titleText.setAttribute("align", "center");
        titleText.setAttribute("position", `0 ${data.height / 2 - 0.03} 0.002`);
        titleText.setAttribute("width", data.width * 1.5);
        titleText.setAttribute("color", "#e0e0e0");
        el.appendChild(titleText);

        // Make panel interactive: follow gaze when grabbed
        el.classList.add("clickable");
        el.setAttribute("class", "clickable");
      },
    });

    AFRAME.registerComponent("follow-camera", {
      schema: {
        distance: { type: "number", default: 1.2 },
        yOffset: { type: "number", default: 0 },
      },
      tick: function () {
        const camera = this.el.sceneEl.camera.el;
        const pos = camera.getAttribute("position");
        const rot = camera.getAttribute("rotation");
        const rad = THREE.MathUtils.degToRad(rot.y);
        this.el.setAttribute("position", {
          x: pos.x - Math.sin(rad) * this.data.distance,
          y: pos.y + this.data.yOffset,
          z: pos.z - Math.cos(rad) * this.data.distance,
        });
        this.el.setAttribute("rotation", { x: 0, y: rot.y, z: 0 });
      },
    });
  </script>
</head>
<body>
  <a-scene webxr="requiredFeatures: local-floor; optionalFeatures: hand-tracking">
    <a-entity id="rig" position="0 1.6 0">
      <a-camera></a-camera>
    </a-entity>

    <!-- Static settings panel at comfortable arm's-reach distance -->
    <a-entity
      spatial-panel="title: Settings; width: 0.5; height: 0.35"
      position="-0.4 1.4 -1.0"
      rotation="0 15 0">
    </a-entity>

    <!-- HUD panel that follows the user's gaze -->
    <a-entity
      spatial-panel="title: Status; width: 0.3; height: 0.15"
      follow-camera="distance: 1.5; yOffset: 0.3">
    </a-entity>

    <a-entity laser-controls="hand: right" raycaster="objects: .clickable"></a-entity>
  </a-scene>
</body>
</html>
```

## Spatial UX Guidelines

- Place UI within ergonomic comfort zones (arm's reach, 15-degree vertical arc).
- Minimize motion sickness through fixed reference frames and vignette effects.
- Build discoverable interactions with visual affordances and audio/haptic feedback.
- Follow spatial design principles: depth hierarchy, gaze-friendly sizing (minimum 1 degree visual angle).
- For cockpit/simulation interfaces: anchor elements to prevent vestibular mismatch, use constraint-driven controls (no free-float motion).
