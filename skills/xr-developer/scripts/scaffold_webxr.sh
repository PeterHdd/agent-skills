#!/usr/bin/env bash
# scaffold_webxr.sh - Scaffold a WebXR project with Three.js boilerplate.
#
# Creates a project directory containing:
#   - index.html with WebXR immersive-vr session request boilerplate
#   - main.js with a basic Three.js scene setup and XR render loop
#   - package.json with three as a dependency
#   - styles.css with minimal reset styles
#
# Usage:
#   scaffold_webxr.sh --name <project-name>

set -euo pipefail

usage() {
    cat <<USAGE
Usage: $(basename "$0") --name <project-name>

Scaffold a WebXR project with Three.js boilerplate.

Options:
  --name <name>   Name for the project directory (required)
  --help          Show this help message and exit

Creates:
  <name>/
    index.html    - HTML with WebXR immersive-vr session request
    main.js       - Three.js scene with XR render loop
    package.json  - Node package with three as dependency
    styles.css    - Minimal CSS reset

Example:
  $(basename "$0") --name my-vr-app
USAGE
}

PROJECT_NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --name requires a value" >&2
                exit 1
            fi
            PROJECT_NAME="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT_NAME" ]]; then
    echo "Error: --name is required" >&2
    usage >&2
    exit 1
fi

# Validate project name (alphanumeric, hyphens, underscores)
if [[ ! "$PROJECT_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Error: Project name must contain only alphanumeric characters, hyphens, and underscores." >&2
    exit 1
fi

if [[ -d "$PROJECT_NAME" ]]; then
    echo "Error: Directory '$PROJECT_NAME' already exists." >&2
    exit 1
fi

echo "## Scaffolding WebXR project: $PROJECT_NAME"
echo ""

mkdir -p "$PROJECT_NAME"

# --- package.json ---
cat > "$PROJECT_NAME/package.json" <<'PACKAGE_EOF'
{
  "name": "PROJECT_NAME_PLACEHOLDER",
  "version": "1.0.0",
  "description": "WebXR project built with Three.js",
  "main": "main.js",
  "scripts": {
    "dev": "npx serve .",
    "start": "npx serve ."
  },
  "dependencies": {
    "three": "^0.170.0"
  },
  "keywords": ["webxr", "vr", "threejs"],
  "license": "MIT"
}
PACKAGE_EOF

# Replace the placeholder with the actual project name
if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/g" "$PROJECT_NAME/package.json"
else
    sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/g" "$PROJECT_NAME/package.json"
fi

# --- styles.css ---
cat > "$PROJECT_NAME/styles.css" <<'CSS_EOF'
/* WebXR Project - Minimal Reset */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #000;
  color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
}

#overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  pointer-events: none;
  z-index: 10;
}

#vr-button {
  pointer-events: auto;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 600;
  border: 2px solid #fff;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

#vr-button:hover {
  background: rgba(255, 255, 255, 0.2);
}

#vr-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

#status {
  pointer-events: none;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}
CSS_EOF

# --- index.html ---
cat > "$PROJECT_NAME/index.html" <<'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WebXR Project</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="overlay">
    <button id="vr-button" disabled>Loading...</button>
    <p id="status"></p>
  </div>

  <!-- Import map for Three.js (use CDN for quick prototyping) -->
  <script type="importmap">
  {
    "imports": {
      "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
    }
  }
  </script>

  <script type="module" src="main.js"></script>
</body>
</html>
HTML_EOF

# --- main.js ---
cat > "$PROJECT_NAME/main.js" <<'JS_EOF'
/**
 * WebXR Three.js Boilerplate
 *
 * Sets up:
 * - Three.js renderer with WebXR enabled
 * - Immersive VR session management
 * - Basic scene with lighting, ground plane, and animated cube
 * - XR-compatible render loop
 */

import * as THREE from 'three';

// --- Scene Setup ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);

const camera = new THREE.PerspectiveCamera(
  70,
  window.innerWidth / window.innerHeight,
  0.01,
  100
);
camera.position.set(0, 1.6, 3); // Approximate standing eye height

// --- Renderer ---
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.xr.enabled = true;
document.body.appendChild(renderer.domElement);

// --- Lighting ---
const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(5, 10, 7);
directionalLight.castShadow = true;
scene.add(directionalLight);

// --- Ground Plane ---
const groundGeometry = new THREE.PlaneGeometry(20, 20);
const groundMaterial = new THREE.MeshStandardMaterial({
  color: 0x2d2d44,
  roughness: 0.9,
});
const ground = new THREE.Mesh(groundGeometry, groundMaterial);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// --- Grid Helper ---
const grid = new THREE.GridHelper(20, 20, 0x444466, 0x333355);
grid.position.y = 0.01;
scene.add(grid);

// --- Interactive Cube ---
const cubeGeometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
const cubeMaterial = new THREE.MeshStandardMaterial({
  color: 0x4fc3f7,
  roughness: 0.3,
  metalness: 0.5,
});
const cube = new THREE.Mesh(cubeGeometry, cubeMaterial);
cube.position.set(0, 1.0, -1.5);
cube.castShadow = true;
scene.add(cube);

// --- WebXR Session Management ---
const vrButton = document.getElementById('vr-button');
const statusEl = document.getElementById('status');

async function checkXRSupport() {
  if (!navigator.xr) {
    vrButton.textContent = 'WebXR Not Available';
    statusEl.textContent = 'Your browser does not support WebXR.';
    return;
  }

  try {
    const supported = await navigator.xr.isSessionSupported('immersive-vr');
    if (supported) {
      vrButton.textContent = 'Enter VR';
      vrButton.disabled = false;
      statusEl.textContent = 'VR headset detected. Click to enter.';
    } else {
      vrButton.textContent = 'VR Not Supported';
      statusEl.textContent = 'immersive-vr sessions are not supported on this device.';
    }
  } catch (err) {
    vrButton.textContent = 'VR Check Failed';
    statusEl.textContent = `Error checking XR support: ${err.message}`;
  }
}

let currentSession = null;

async function onVRButtonClick() {
  if (currentSession) {
    await currentSession.end();
    return;
  }

  try {
    const session = await navigator.xr.requestSession('immersive-vr', {
      optionalFeatures: ['local-floor', 'bounded-floor', 'hand-tracking'],
    });

    session.addEventListener('end', () => {
      currentSession = null;
      vrButton.textContent = 'Enter VR';
      statusEl.textContent = 'Session ended.';
    });

    await renderer.xr.setSession(session);
    currentSession = session;
    vrButton.textContent = 'Exit VR';
    statusEl.textContent = 'VR session active.';
  } catch (err) {
    statusEl.textContent = `Failed to start VR: ${err.message}`;
  }
}

vrButton.addEventListener('click', onVRButtonClick);
checkXRSupport();

// --- Animation Loop (XR-compatible) ---
const clock = new THREE.Clock();

function animate() {
  const elapsed = clock.getElapsedTime();

  // Gentle rotation and float for the cube
  cube.rotation.x = elapsed * 0.5;
  cube.rotation.y = elapsed * 0.7;
  cube.position.y = 1.0 + Math.sin(elapsed) * 0.15;

  renderer.render(scene, camera);
}

renderer.setAnimationLoop(animate);

// --- Window Resize ---
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
JS_EOF

echo "### Files created:"
echo ""
echo "- \`$PROJECT_NAME/index.html\`   - HTML with WebXR session management"
echo "- \`$PROJECT_NAME/main.js\`      - Three.js scene with XR render loop"
echo "- \`$PROJECT_NAME/package.json\` - Node package (run \`npm install\` to fetch deps)"
echo "- \`$PROJECT_NAME/styles.css\`   - Minimal CSS reset"
echo ""
echo "### Next steps:"
echo ""
echo "1. \`cd $PROJECT_NAME\`"
echo "2. \`npm install\`"
echo "3. \`npm run dev\` (serves on localhost)"
echo "4. Open in a WebXR-capable browser or use a VR headset"
echo ""
echo "Done."
