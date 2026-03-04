# Task Example: TaskFlow Task Management App

Below is a complete task breakdown for a fictional project. This demonstrates the expected format, level of detail, and tone.

```markdown
# TaskFlow Development Tasks

## Specification Summary
**Quoted Requirements**:
- "Users can create, edit, and delete tasks organized into boards"
- "Each board has three columns: To Do, In Progress, Done"
- "Users authenticate via email/password"
- "Drag-and-drop to move tasks between columns"
- "Real-time updates when multiple users view the same board"

**Technical Stack**: React 18, Node.js/Express, PostgreSQL, Socket.IO
**Target Timeline**: 4 weeks

## Clarifications Needed
1. **Max board members**: Spec says "multiple users" but does not define a limit.
   Assumed default: 20 users per board. Flagged for stakeholder review.
2. **Task attachments**: Not mentioned in spec. Excluded from scope.

## Development Tasks

### [x] Task 0: Project Setup
**Description**: Initialize monorepo with React frontend, Express backend, and PostgreSQL schema. Configure ESLint, Prettier, and CI pipeline.
**Estimate**: 3 hours (high confidence)
**Acceptance Criteria**:
- `npm run dev` starts both frontend (port 3000) and backend (port 4000) without errors
- `npm run lint` and `npm run typecheck` pass with zero warnings
- PostgreSQL connection established and health-check endpoint returns 200
**Files**:
- `package.json`, `tsconfig.json`, `.eslintrc.json`
- `apps/api/src/index.ts`, `apps/web/src/main.tsx`
- `docker-compose.yml` (PostgreSQL service)
**Spec Reference**: Technical requirements section

### [ ] Task 1: User Authentication
**Description**: Implement email/password registration and login with JWT tokens. Include input validation and error responses.
**Estimate**: 6 hours (high confidence)
**Acceptance Criteria**:
- POST `/api/auth/register` with valid email/password returns 201 and a JWT
- POST `/api/auth/register` with duplicate email returns 409
- POST `/api/auth/login` with correct credentials returns 200 and a JWT
- POST `/api/auth/login` with wrong password returns 401
- JWT expires after 24 hours; requests with expired tokens return 401
- Passwords are hashed with bcrypt (cost factor 12)
**Files**:
- `apps/api/src/routes/auth.ts`
- `apps/api/src/middleware/authenticate.ts`
- `apps/api/src/models/user.ts`
- `migrations/001_create_users.sql`
**Spec Reference**: "Users authenticate via email/password"

### [ ] Task 2: Board CRUD and Column Structure
**Description**: Create API endpoints and UI for creating, listing, and deleting boards. Each board is initialized with three columns: To Do, In Progress, Done.
**Estimate**: 5 hours (high confidence)
**Acceptance Criteria**:
- POST `/api/boards` creates a board with exactly three columns and returns the board object
- GET `/api/boards` returns all boards for the authenticated user
- DELETE `/api/boards/:id` returns 204 and removes the board and its tasks
- Frontend displays a board list view with a "New Board" button
- Clicking a board navigates to `/boards/:id` showing three empty columns
**Files**:
- `apps/api/src/routes/boards.ts`
- `apps/api/src/models/board.ts`
- `apps/web/src/pages/BoardList.tsx`, `apps/web/src/pages/BoardView.tsx`
- `migrations/002_create_boards_and_columns.sql`
**Spec Reference**: "organized into boards", "three columns: To Do, In Progress, Done"

### [ ] Task 3: Task CRUD Within Boards
**Description**: Implement creating, editing, and deleting tasks within board columns. Tasks have a title (required) and description (optional).
**Estimate**: 5 hours (high confidence)
**Acceptance Criteria**:
- POST `/api/boards/:id/tasks` with a title creates a task in the "To Do" column
- PATCH `/api/tasks/:id` updates title and/or description; returns the updated task
- DELETE `/api/tasks/:id` returns 204 and removes the task
- Frontend shows an inline "Add task" input at the bottom of each column
- Editing a task opens a modal with title and description fields
- Deleting a task prompts a confirmation dialog before removal
**Files**:
- `apps/api/src/routes/tasks.ts`
- `apps/api/src/models/task.ts`
- `apps/web/src/components/TaskCard.tsx`, `apps/web/src/components/TaskModal.tsx`
- `migrations/003_create_tasks.sql`
**Spec Reference**: "Users can create, edit, and delete tasks"

### [ ] Task 4: Drag-and-Drop Between Columns
**Description**: Add drag-and-drop support to move tasks between columns and reorder within a column. Persist column and position changes to the backend.
**Estimate**: 6 hours (medium confidence -- library integration complexity)
**Acceptance Criteria**:
- Dragging a task from "To Do" to "In Progress" visually moves the card and persists the change on page reload
- Reordering tasks within a column persists the new order
- PATCH `/api/tasks/:id/move` accepts `columnId` and `position`; returns 200
- Drag preview shows a semi-transparent copy of the task card
**Files**:
- `apps/web/src/components/BoardColumns.tsx` (drag-and-drop wrapper)
- `apps/api/src/routes/tasks.ts` (add move endpoint)
**Spec Reference**: "Drag-and-drop to move tasks between columns"

## Quality Checklist
- [ ] Every API endpoint has input validation and returns appropriate HTTP status codes
- [ ] All database changes use migration files (no manual schema edits)
- [ ] Frontend routes are protected; unauthenticated users redirect to login
- [ ] No hardcoded secrets; all config via environment variables
- [ ] `npm test` passes with >80% line coverage on API routes
```
