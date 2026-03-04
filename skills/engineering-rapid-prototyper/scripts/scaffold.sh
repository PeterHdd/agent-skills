#!/usr/bin/env bash
#
# scaffold.sh -- Scaffold a basic project structure.
#
# Creates a project skeleton with package.json and basic config files.
# Does NOT install any dependencies.
#
# Usage:
#   ./scaffold.sh --type nextjs --name my-app
#   ./scaffold.sh --type vite --name dashboard
#   ./scaffold.sh --type express --name api-server
#   ./scaffold.sh --help

set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") --type <TYPE> --name <NAME> [OPTIONS]

Scaffold a basic project structure with package.json and config files.

Required options:
  --type TYPE    Project type: nextjs, vite, or express
  --name NAME    Project name (used as directory name and in package.json)

Optional:
  --out DIR      Parent directory to create the project in (default: current directory)
  -h, --help     Show this help message

Supported project types:
  nextjs    Next.js app with App Router (TypeScript)
  vite      Vite + React app (TypeScript)
  express   Express.js API server (TypeScript)

This script creates the directory structure and config files only.
It does NOT run npm install or any package manager commands.

Exit codes:
  0   Project scaffolded successfully
  1   Error during scaffolding
  2   Invalid arguments

Examples:
  $(basename "$0") --type nextjs --name my-app
  $(basename "$0") --type vite --name dashboard --out /tmp
  $(basename "$0") --type express --name api-server
EOF
}

# --- Argument parsing ---

PROJECT_TYPE=""
PROJECT_NAME=""
OUT_DIR="."

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --type)
            if [[ $# -lt 2 ]]; then
                echo "Error: --type requires a value" >&2
                exit 2
            fi
            PROJECT_TYPE="$2"
            shift 2
            ;;
        --name)
            if [[ $# -lt 2 ]]; then
                echo "Error: --name requires a value" >&2
                exit 2
            fi
            PROJECT_NAME="$2"
            shift 2
            ;;
        --out)
            if [[ $# -lt 2 ]]; then
                echo "Error: --out requires a value" >&2
                exit 2
            fi
            OUT_DIR="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            echo "Error: Unexpected argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$PROJECT_TYPE" ]]; then
    echo "Error: --type is required" >&2
    echo "" >&2
    usage >&2
    exit 2
fi

if [[ -z "$PROJECT_NAME" ]]; then
    echo "Error: --name is required" >&2
    echo "" >&2
    usage >&2
    exit 2
fi

case "$PROJECT_TYPE" in
    nextjs|vite|express) ;;
    *)
        echo "Error: Invalid project type: $PROJECT_TYPE (must be nextjs, vite, or express)" >&2
        exit 2
        ;;
esac

PROJECT_DIR="$OUT_DIR/$PROJECT_NAME"

if [[ -d "$PROJECT_DIR" ]]; then
    echo "Error: Directory already exists: $PROJECT_DIR" >&2
    exit 1
fi

# --- Shared helpers ---

create_file() {
    local filepath="$1"
    local content="$2"
    mkdir -p "$(dirname "$filepath")"
    printf '%s\n' "$content" > "$filepath"
}

create_gitignore() {
    create_file "$PROJECT_DIR/.gitignore" 'node_modules/
dist/
build/
.next/
.env
.env.local
*.log
.DS_Store'
}

create_env_example() {
    create_file "$PROJECT_DIR/.env.example" '# Application environment variables
NODE_ENV=development
PORT=3000'
}

# --- Scaffold: Next.js ---

scaffold_nextjs() {
    mkdir -p "$PROJECT_DIR"

    create_file "$PROJECT_DIR/package.json" "{
  \"name\": \"$PROJECT_NAME\",
  \"version\": \"0.1.0\",
  \"private\": true,
  \"scripts\": {
    \"dev\": \"next dev\",
    \"build\": \"next build\",
    \"start\": \"next start\",
    \"lint\": \"next lint\"
  },
  \"dependencies\": {
    \"next\": \"^14.0.0\",
    \"react\": \"^18.2.0\",
    \"react-dom\": \"^18.2.0\"
  },
  \"devDependencies\": {
    \"@types/node\": \"^20.0.0\",
    \"@types/react\": \"^18.2.0\",
    \"@types/react-dom\": \"^18.2.0\",
    \"typescript\": \"^5.3.0\"
  }
}"

    create_file "$PROJECT_DIR/tsconfig.json" '{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}'

    create_file "$PROJECT_DIR/next.config.js" "/** @type {import('next').NextConfig} */
const nextConfig = {}

module.exports = nextConfig"

    # App Router structure
    mkdir -p "$PROJECT_DIR/src/app"

    create_file "$PROJECT_DIR/src/app/layout.tsx" "export const metadata = {
  title: '$PROJECT_NAME',
  description: 'A Next.js application',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang=\"en\">
      <body>{children}</body>
    </html>
  )
}"

    create_file "$PROJECT_DIR/src/app/page.tsx" "export default function Home() {
  return (
    <main>
      <h1>$PROJECT_NAME</h1>
      <p>Welcome to your Next.js application.</p>
    </main>
  )
}"

    create_file "$PROJECT_DIR/src/app/globals.css" "* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  max-width: 100vw;
  overflow-x: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
}"

    mkdir -p "$PROJECT_DIR/public"
    create_gitignore
    create_env_example
}

# --- Scaffold: Vite ---

scaffold_vite() {
    mkdir -p "$PROJECT_DIR"

    create_file "$PROJECT_DIR/package.json" "{
  \"name\": \"$PROJECT_NAME\",
  \"version\": \"0.1.0\",
  \"private\": true,
  \"type\": \"module\",
  \"scripts\": {
    \"dev\": \"vite\",
    \"build\": \"tsc && vite build\",
    \"preview\": \"vite preview\"
  },
  \"dependencies\": {
    \"react\": \"^18.2.0\",
    \"react-dom\": \"^18.2.0\"
  },
  \"devDependencies\": {
    \"@types/react\": \"^18.2.0\",
    \"@types/react-dom\": \"^18.2.0\",
    \"@vitejs/plugin-react\": \"^4.2.0\",
    \"typescript\": \"^5.3.0\",
    \"vite\": \"^5.0.0\"
  }
}"

    create_file "$PROJECT_DIR/tsconfig.json" '{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}'

    create_file "$PROJECT_DIR/vite.config.ts" "import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})"

    create_file "$PROJECT_DIR/index.html" "<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>$PROJECT_NAME</title>
  </head>
  <body>
    <div id=\"root\"></div>
    <script type=\"module\" src=\"/src/main.tsx\"></script>
  </body>
</html>"

    mkdir -p "$PROJECT_DIR/src"

    create_file "$PROJECT_DIR/src/main.tsx" "import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"

    create_file "$PROJECT_DIR/src/App.tsx" "function App() {
  return (
    <div>
      <h1>$PROJECT_NAME</h1>
      <p>Welcome to your Vite + React application.</p>
    </div>
  )
}

export default App"

    create_file "$PROJECT_DIR/src/index.css" "* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
}"

    create_file "$PROJECT_DIR/src/vite-env.d.ts" '/// <reference types="vite/client" />'

    mkdir -p "$PROJECT_DIR/public"
    create_gitignore
    create_env_example
}

# --- Scaffold: Express ---

scaffold_express() {
    mkdir -p "$PROJECT_DIR"

    create_file "$PROJECT_DIR/package.json" "{
  \"name\": \"$PROJECT_NAME\",
  \"version\": \"0.1.0\",
  \"private\": true,
  \"scripts\": {
    \"dev\": \"ts-node --esm src/index.ts\",
    \"build\": \"tsc\",
    \"start\": \"node dist/index.js\"
  },
  \"dependencies\": {
    \"express\": \"^4.18.0\"
  },
  \"devDependencies\": {
    \"@types/express\": \"^4.17.0\",
    \"@types/node\": \"^20.0.0\",
    \"ts-node\": \"^10.9.0\",
    \"typescript\": \"^5.3.0\"
  }
}"

    create_file "$PROJECT_DIR/tsconfig.json" '{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}'

    mkdir -p "$PROJECT_DIR/src/routes"
    mkdir -p "$PROJECT_DIR/src/middleware"

    create_file "$PROJECT_DIR/src/index.ts" "import express from 'express'
import { healthRouter } from './routes/health'

const app = express()
const PORT = process.env.PORT || 3000

app.use(express.json())

// Routes
app.use('/health', healthRouter)

app.get('/', (_req, res) => {
  res.json({ message: 'Welcome to $PROJECT_NAME' })
})

app.listen(PORT, () => {
  console.log(\`Server running on http://localhost:\${PORT}\`)
})"

    create_file "$PROJECT_DIR/src/routes/health.ts" "import { Router } from 'express'

export const healthRouter = Router()

healthRouter.get('/', (_req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  })
})"

    create_file "$PROJECT_DIR/src/middleware/errorHandler.ts" "import { Request, Response, NextFunction } from 'express'

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response,
  _next: NextFunction
) {
  console.error(err.stack)
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined,
  })
}"

    create_gitignore
    create_env_example
}

# --- Main ---

case "$PROJECT_TYPE" in
    nextjs)  scaffold_nextjs  ;;
    vite)    scaffold_vite    ;;
    express) scaffold_express ;;
esac

# --- Output report ---

echo "## Project Scaffolded: \`$PROJECT_NAME\`"
echo ""
echo "- **Type**: $PROJECT_TYPE"
echo "- **Location**: \`$PROJECT_DIR\`"
echo ""

echo "### Files Created"
echo ""
echo "\`\`\`"
if command -v find &>/dev/null; then
    (cd "$PROJECT_DIR" && find . -type f | sort | sed 's|^\./||')
fi
echo "\`\`\`"
echo ""

echo "### Next Steps"
echo ""
echo "1. \`cd $PROJECT_DIR\`"
echo "2. \`npm install\`"

case "$PROJECT_TYPE" in
    nextjs)
        echo "3. \`npm run dev\` -- starts the Next.js dev server"
        ;;
    vite)
        echo "3. \`npm run dev\` -- starts the Vite dev server"
        ;;
    express)
        echo "3. \`npm run dev\` -- starts the Express server with ts-node"
        ;;
esac

echo ""
echo "---"
echo "**Scaffold complete. No dependencies were installed.**"
