---
name: xr-developer
description: "Build immersive AR/VR/XR applications with spatial interfaces, multi-input support, and cross-device compatibility. Use when you need WebXR development with A-Frame, Three.js, or Babylon.js, spatial UI/UX design, cockpit or simulation interfaces, gaze and hand tracking, occlusion culling, LOD optimization, HUD and floating menu design, or 72-90fps rendering on standalone headsets."
metadata:
  version: "1.0.0"
---

# WebXR Development Guide

Build immersive, performant AR/VR/XR applications with spatial interfaces, multi-input support, and cross-device compatibility using WebXR, A-Frame, Three.js, and Babylon.js.

## Session Lifecycle

```
navigator.xr.requestSession('immersive-vr')
  -> session.requestReferenceSpace('local-floor')
  -> session.requestAnimationFrame(onXRFrame)
  -> session.end()  // cleanup on onend event
```

Always handle `onend` for cleanup. Follow WebXR spec for `immersive-vr` and `immersive-ar` session types.

## Cross-Device Compatibility

| Device | Session Type | Primary Input | Notes |
|--------|-------------|---------------|-------|
| Meta Quest 2/3/Pro | `immersive-vr` | Controllers + hand tracking | Test both input modes |
| Apple Vision Pro | `immersive-vr` | Hand tracking + eye tracking | Hand tracking primary |
| HoloLens 2 | `immersive-ar` | Hand tracking + gaze | AR session type |
| Mobile AR | `immersive-ar` | Touch + device motion | Fallback to inline if needed |

Handle capability differences via feature detection (not user-agent sniffing). Adapt interaction models per device.

## Performance

### Frame Budget

- Target 72fps on Quest 3, 90fps on Quest Pro.
- Keep frame budget under 11ms for 90fps targets.
- Optimize rendering: occlusion culling, LOD, shader tuning, draw call batching.
- Handle graceful fallback for non-XR browsers with progressive enhancement.

### Optimization Checklist

- Profile GPU and CPU on-device (not just desktop).
- Reduce draw calls via instancing and mesh merging.
- Implement LOD (level of detail) for distant objects.
- Use texture atlases to reduce material switches.
- Test with WebXR emulators and real devices (at least 2 runtimes before shipping).

## Code Examples

See [WebXR with Three.js Guide](references/webxr-threejs.md) for full session setup, controller models, hand tracking pinch detection, controller input handling, and the input fallback chain.

See [Spatial UI with A-Frame Guide](references/spatial-ui.md) for the spatial-panel component, follow-camera HUD component, and spatial UX guidelines.

## Workflow

1. **Define scope**: Target devices, interaction model, session type (VR/AR/inline).
2. **Scaffold**: Set up renderer, XR session management, input handling.
3. **Build interactions**: Implement spatial UI, input methods, physics/raycasting.
4. **Optimize**: Profile GPU/CPU, reduce draw calls, implement LOD, test on-device.
5. **Ship**: Test across target devices, implement fallbacks, document known limitations.

## Scripts

### `scripts/scaffold_webxr.sh`
Create a minimal WebXR project structure with Three.js and a working VR hello-world that renders a rotating cube. Generates index.html (with Three.js CDN + WebXR boilerplate), main.js (XR session setup + render loop), styles.css, and package.json (with a dev server).

```bash
scripts/scaffold_webxr.sh --name my-vr-app
scripts/scaffold_webxr.sh --name vr-demo
```

### `scripts/check_webxr_compat.py`
Check JavaScript/HTML files for common WebXR compatibility issues: deprecated WebVR APIs (navigator.getVRDisplays), missing feature detection, missing session support checks, and vendor-prefixed extensions. Outputs a structured markdown compatibility report with line numbers and suggestions.

```bash
scripts/check_webxr_compat.py main.js
scripts/check_webxr_compat.py src/
scripts/check_webxr_compat.py --output report.md src/xr-scene.js
```

## Key Specifications

- [WebXR Device API](https://www.w3.org/TR/webxr/)
- [WebXR Hand Input](https://www.w3.org/TR/webxr-hand-input-1/)
- [A-Frame](https://aframe.io/docs/)
- [Three.js WebXR](https://threejs.org/docs/#manual/en/introduction/How-to-create-VR-content)
