# Full Stack Integration Patterns

Concrete wiring for the recommended stack: Next.js 14 + Prisma + Supabase + Clerk.

## Prisma Schema

A realistic SaaS prototype schema with users, teams, projects, and invitations.

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_URL")
}

enum Role {
  OWNER
  ADMIN
  MEMBER
}

enum InvitationStatus {
  PENDING
  ACCEPTED
  EXPIRED
}

model User {
  id        String   @id @default(cuid())
  clerkId   String   @unique
  email     String   @unique
  name      String?
  avatarUrl String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  memberships TeamMember[]
  projects    Project[]
  invitations Invitation[] @relation("InvitedBy")
}

model Team {
  id        String   @id @default(cuid())
  name      String
  slug      String   @unique
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  members     TeamMember[]
  projects    Project[]
  invitations Invitation[]
}

model TeamMember {
  id     String @id @default(cuid())
  role   Role   @default(MEMBER)
  userId String
  teamId String

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  team Team @relation(fields: [teamId], references: [id], onDelete: Cascade)

  @@unique([userId, teamId])
}

model Project {
  id          String   @id @default(cuid())
  name        String
  description String?
  isPublic    Boolean  @default(false)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  ownerId String
  teamId  String

  owner User @relation(fields: [ownerId], references: [id])
  team  Team @relation(fields: [teamId], references: [id], onDelete: Cascade)
}

model Invitation {
  id        String           @id @default(cuid())
  email     String
  role      Role             @default(MEMBER)
  status    InvitationStatus @default(PENDING)
  token     String           @unique @default(cuid())
  expiresAt DateTime
  createdAt DateTime         @default(now())

  teamId    String
  inviterId String

  team    Team @relation(fields: [teamId], references: [id], onDelete: Cascade)
  inviter User @relation("InvitedBy", fields: [inviterId], references: [id])

  @@index([email, teamId])
}
```

## Supabase + Prisma Setup

Prisma client initialization with connection pooling for serverless environments.

```typescript
// lib/db.ts
import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query"] : [],
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
```

Environment variables -- `DATABASE_URL` uses a pooled connection (port 6543) for serverless, while `DIRECT_URL` connects directly (port 5432) for migrations:

```env
# .env.local
DATABASE_URL="postgresql://example_user:example_pass@pooler.example.invalid:6543/appdb?pgbouncer=true"
DIRECT_URL="postgresql://example_user:example_pass@db.example.invalid:5432/appdb"
```

## Clerk Auth Middleware

Protect routes and redirect unauthenticated users.

```typescript
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
```

Reading the current user in a server component:

```typescript
// app/dashboard/page.tsx
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const clerkUser = await currentUser();
  if (!clerkUser) redirect("/sign-in");

  const user = await prisma.user.findUnique({
    where: { clerkId: clerkUser.id },
    include: { memberships: { include: { team: true } } },
  });

  if (!user) redirect("/onboarding");

  return (
    <div>
      <h1>Welcome, {user.name}</h1>
      <ul>
        {user.memberships.map((m) => (
          <li key={m.id}>{m.team.name} ({m.role})</li>
        ))}
      </ul>
    </div>
  );
}
```

## Server Actions

Next.js server actions for project CRUD with auth checks.

```typescript
// app/actions/projects.ts
"use server";

import { auth } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { z } from "zod";

const CreateProjectSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  teamId: z.string().cuid(),
  isPublic: z.boolean().default(false),
});

const UpdateProjectSchema = z.object({
  id: z.string().cuid(),
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  isPublic: z.boolean().optional(),
});

async function getAuthUser() {
  const { userId } = await auth();
  if (!userId) throw new Error("Unauthorized");
  const user = await prisma.user.findUnique({ where: { clerkId: userId } });
  if (!user) throw new Error("User not found");
  return user;
}

export async function createProject(formData: FormData) {
  const user = await getAuthUser();
  const parsed = CreateProjectSchema.parse({
    name: formData.get("name"),
    description: formData.get("description"),
    teamId: formData.get("teamId"),
    isPublic: formData.get("isPublic") === "true",
  });

  const project = await prisma.project.create({
    data: { ...parsed, ownerId: user.id },
  });

  revalidatePath(`/teams/${parsed.teamId}/projects`);
  return project;
}

export async function updateProject(formData: FormData) {
  const user = await getAuthUser();
  const parsed = UpdateProjectSchema.parse({
    id: formData.get("id"),
    name: formData.get("name") || undefined,
    description: formData.get("description") || undefined,
    isPublic: formData.has("isPublic")
      ? formData.get("isPublic") === "true"
      : undefined,
  });

  const existing = await prisma.project.findUnique({
    where: { id: parsed.id },
  });
  if (!existing || existing.ownerId !== user.id) {
    throw new Error("Not found or not authorized");
  }

  const { id, ...data } = parsed;
  const project = await prisma.project.update({ where: { id }, data });
  revalidatePath(`/teams/${existing.teamId}/projects`);
  return project;
}

export async function deleteProject(projectId: string) {
  const user = await getAuthUser();
  const existing = await prisma.project.findUnique({
    where: { id: projectId },
  });
  if (!existing || existing.ownerId !== user.id) {
    throw new Error("Not found or not authorized");
  }

  await prisma.project.delete({ where: { id: projectId } });
  revalidatePath(`/teams/${existing.teamId}/projects`);
}
```

## tRPC Setup (Alternative to Server Actions)

Router definition with Zod validation and auth context.

```typescript
// server/trpc.ts
import { initTRPC, TRPCError } from "@trpc/server";
import { auth } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import superjson from "superjson";

export const createTRPCContext = async () => {
  const { userId } = await auth();
  return { userId, prisma };
};

const t = initTRPC.context<typeof createTRPCContext>().create({
  transformer: superjson,
});

const isAuthed = t.middleware(async ({ ctx, next }) => {
  if (!ctx.userId) throw new TRPCError({ code: "UNAUTHORIZED" });
  const user = await ctx.prisma.user.findUnique({
    where: { clerkId: ctx.userId },
  });
  if (!user) throw new TRPCError({ code: "NOT_FOUND", message: "User not found" });
  return next({ ctx: { ...ctx, user } });
});

export const router = t.router;
export const publicProcedure = t.procedure;
export const protectedProcedure = t.procedure.use(isAuthed);
```

```typescript
// server/routers/projects.ts
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

export const projectRouter = router({
  list: protectedProcedure
    .input(z.object({ teamId: z.string().cuid() }))
    .query(async ({ ctx, input }) => {
      return ctx.prisma.project.findMany({
        where: { teamId: input.teamId },
        orderBy: { createdAt: "desc" },
      });
    }),

  create: protectedProcedure
    .input(z.object({
      name: z.string().min(1).max(100),
      description: z.string().max(500).optional(),
      teamId: z.string().cuid(),
    }))
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.project.create({
        data: { ...input, ownerId: ctx.user.id },
      });
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.string().cuid() }))
    .mutation(async ({ ctx, input }) => {
      const project = await ctx.prisma.project.findUnique({
        where: { id: input.id },
      });
      if (!project || project.ownerId !== ctx.user.id) {
        throw new Error("Not authorized");
      }
      return ctx.prisma.project.delete({ where: { id: input.id } });
    }),
});
```

Client-side usage in a React component:

```typescript
// app/teams/[teamId]/projects/page.tsx
"use client";

import { trpc } from "@/lib/trpc-client";
import { Button } from "@/components/ui/button";

export default function ProjectsPage({ params }: { params: { teamId: string } }) {
  const { data: projects, isLoading } = trpc.project.list.useQuery({
    teamId: params.teamId,
  });
  const utils = trpc.useUtils();
  const createMutation = trpc.project.create.useMutation({
    onSuccess: () => utils.project.list.invalidate(),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <Button
        onClick={() =>
          createMutation.mutate({
            name: "New Project",
            teamId: params.teamId,
          })
        }
      >
        New Project
      </Button>
      <ul>
        {projects?.map((p) => (
          <li key={p.id}>{p.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

## File Upload with Supabase Storage

API route that generates a presigned upload URL, plus a client-side upload component with progress tracking.

```typescript
// app/api/upload/route.ts
import { auth } from "@clerk/nextjs/server";
import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { filename, contentType } = await request.json();
  const path = `${userId}/${Date.now()}-${filename}`;

  const { data, error } = await supabase.storage
    .from("uploads")
    .createSignedUploadUrl(path);

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ signedUrl: data.signedUrl, path });
}
```

```tsx
// components/file-upload.tsx
"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export function FileUpload({ onComplete }: { onComplete: (path: string) => void }) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setProgress(0);

    const res = await fetch("/api/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, contentType: file.type }),
    });
    const { signedUrl, path } = await res.json();

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    });
    xhr.addEventListener("load", () => {
      setUploading(false);
      onComplete(path);
    });
    xhr.open("PUT", signedUrl);
    xhr.setRequestHeader("Content-Type", file.type);
    xhr.send(file);
  }, [onComplete]);

  return (
    <div className="space-y-2">
      <input
        type="file"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        disabled={uploading}
      />
      {uploading && <Progress value={progress} className="w-full" />}
    </div>
  );
}
```

## Email with Resend

Send transactional emails using Resend with a React Email template.

```typescript
// lib/email.ts
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendInvitationEmail(
  to: string,
  inviterName: string,
  teamName: string,
  inviteLink: string
) {
  return resend.emails.send({
    from: "noreply@yourdomain.com",
    to,
    subject: `${inviterName} invited you to join ${teamName}`,
    react: InvitationEmail({ inviterName, teamName, inviteLink }),
  });
}

export async function sendWelcomeEmail(to: string, name: string) {
  return resend.emails.send({
    from: "noreply@yourdomain.com",
    to,
    subject: "Welcome to the platform!",
    react: WelcomeEmail({ name }),
  });
}
```

```tsx
// emails/invitation.tsx
import { Html, Head, Body, Container, Text, Button, Hr } from "@react-email/components";

export function InvitationEmail({
  inviterName,
  teamName,
  inviteLink,
}: {
  inviterName: string;
  teamName: string;
  inviteLink: string;
}) {
  return (
    <Html>
      <Head />
      <Body style={{ fontFamily: "sans-serif", padding: "20px" }}>
        <Container>
          <Text>Hi there,</Text>
          <Text>
            {inviterName} has invited you to join <strong>{teamName}</strong>.
          </Text>
          <Button
            href={inviteLink}
            style={{
              backgroundColor: "#0f172a",
              color: "#fff",
              padding: "12px 24px",
              borderRadius: "6px",
            }}
          >
            Accept Invitation
          </Button>
          <Hr />
          <Text style={{ color: "#6b7280", fontSize: "14px" }}>
            This invitation expires in 7 days.
          </Text>
        </Container>
      </Body>
    </Html>
  );
}
```
