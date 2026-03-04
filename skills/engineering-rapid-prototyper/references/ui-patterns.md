# Rapid UI Patterns with shadcn/ui

Copy-pasteable UI patterns built on shadcn/ui, @tanstack/react-table, cmdk, and Zustand.

## Data Table with Sorting, Filtering, and Pagination

Column definitions and a reusable DataTable component with a search toolbar.

```typescript
// lib/columns.tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";
import { ArrowUpDown, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type Project = {
  id: string;
  name: string;
  status: "active" | "archived" | "draft";
  createdAt: string;
  owner: string;
};

export const columns: ColumnDef<Project>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Name
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.getValue<string>("status");
      const colors: Record<string, string> = {
        active: "bg-green-100 text-green-800",
        archived: "bg-gray-100 text-gray-800",
        draft: "bg-yellow-100 text-yellow-800",
      };
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status]}`}>
          {status}
        </span>
      );
    },
  },
  { accessorKey: "owner", header: "Owner" },
  { accessorKey: "createdAt", header: "Created" },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => navigator.clipboard.writeText(row.original.id)}>
            Copy ID
          </DropdownMenuItem>
          <DropdownMenuItem>Edit</DropdownMenuItem>
          <DropdownMenuItem className="text-red-600">Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
];
```

```tsx
// components/data-table.tsx
"use client";

import { useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  SortingState,
  ColumnFiltersState,
  useReactTable,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchKey?: string;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchKey = "name",
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    state: { sorting, columnFilters },
  });

  return (
    <div className="space-y-4">
      <Input
        placeholder={`Search by ${searchKey}...`}
        value={(table.getColumn(searchKey)?.getFilterValue() as string) ?? ""}
        onChange={(e) => table.getColumn(searchKey)?.setFilterValue(e.target.value)}
        className="max-w-sm"
      />
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
        </span>
        <div className="space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
```

## Command Palette

Global command palette with search, grouped actions, and Cmd+K keyboard shortcut.

```tsx
// components/command-palette.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  LayoutDashboard,
  Settings,
  Users,
  FolderOpen,
  Moon,
  Sun,
  LogOut,
} from "lucide-react";
import { useTheme } from "next-themes";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { setTheme } = useTheme();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const navigate = (path: string) => {
    setOpen(false);
    router.push(path);
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => navigate("/dashboard")}>
            <LayoutDashboard className="mr-2 h-4 w-4" /> Dashboard
          </CommandItem>
          <CommandItem onSelect={() => navigate("/projects")}>
            <FolderOpen className="mr-2 h-4 w-4" /> Projects
          </CommandItem>
          <CommandItem onSelect={() => navigate("/team")}>
            <Users className="mr-2 h-4 w-4" /> Team Members
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Settings">
          <CommandItem onSelect={() => navigate("/settings")}>
            <Settings className="mr-2 h-4 w-4" /> Settings
          </CommandItem>
          <CommandItem onSelect={() => { setTheme("light"); setOpen(false); }}>
            <Sun className="mr-2 h-4 w-4" /> Light Mode
          </CommandItem>
          <CommandItem onSelect={() => { setTheme("dark"); setOpen(false); }}>
            <Moon className="mr-2 h-4 w-4" /> Dark Mode
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Account">
          <CommandItem onSelect={() => navigate("/sign-out")}>
            <LogOut className="mr-2 h-4 w-4" /> Sign Out
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
```

## Multi-Step Form Wizard

Three-step form (details, preferences, confirmation) with Zustand state management and a progress indicator.

```typescript
// store/form-wizard.ts
import { create } from "zustand";

type Step = 1 | 2 | 3;

interface FormData {
  name: string;
  email: string;
  company: string;
  plan: "free" | "pro" | "enterprise";
  notifications: boolean;
  newsletter: boolean;
}

interface WizardStore {
  step: Step;
  data: FormData;
  setStep: (step: Step) => void;
  updateData: (partial: Partial<FormData>) => void;
  reset: () => void;
}

const initialData: FormData = {
  name: "",
  email: "",
  company: "",
  plan: "free",
  notifications: true,
  newsletter: false,
};

export const useWizardStore = create<WizardStore>((set) => ({
  step: 1,
  data: initialData,
  setStep: (step) => set({ step }),
  updateData: (partial) => set((s) => ({ data: { ...s.data, ...partial } })),
  reset: () => set({ step: 1, data: initialData }),
}));
```

```tsx
// components/form-wizard.tsx
"use client";

import { useWizardStore } from "@/store/form-wizard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { CheckCircle2 } from "lucide-react";

function StepIndicator() {
  const step = useWizardStore((s) => s.step);
  const labels = ["Details", "Preferences", "Confirm"];
  return (
    <div className="flex items-center gap-2 mb-8">
      {labels.map((label, i) => (
        <div key={label} className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              i + 1 <= step
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {i + 1 < step ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
          </div>
          <span className="text-sm hidden sm:inline">{label}</span>
          {i < labels.length - 1 && <div className="w-8 h-px bg-border" />}
        </div>
      ))}
    </div>
  );
}

function StepDetails() {
  const { data, updateData, setStep } = useWizardStore();
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="name">Name</Label>
        <Input id="name" value={data.name} onChange={(e) => updateData({ name: e.target.value })} />
      </div>
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" value={data.email} onChange={(e) => updateData({ email: e.target.value })} />
      </div>
      <div>
        <Label htmlFor="company">Company</Label>
        <Input id="company" value={data.company} onChange={(e) => updateData({ company: e.target.value })} />
      </div>
      <Button onClick={() => setStep(2)} disabled={!data.name || !data.email}>
        Next
      </Button>
    </div>
  );
}

function StepPreferences() {
  const { data, updateData, setStep } = useWizardStore();
  return (
    <div className="space-y-6">
      <div>
        <Label>Plan</Label>
        <RadioGroup
          value={data.plan}
          onValueChange={(v) => updateData({ plan: v as "free" | "pro" | "enterprise" })}
          className="mt-2 space-y-2"
        >
          {(["free", "pro", "enterprise"] as const).map((plan) => (
            <div key={plan} className="flex items-center space-x-2">
              <RadioGroupItem value={plan} id={plan} />
              <Label htmlFor={plan} className="capitalize">{plan}</Label>
            </div>
          ))}
        </RadioGroup>
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="notifications">Email notifications</Label>
        <Switch
          id="notifications"
          checked={data.notifications}
          onCheckedChange={(v) => updateData({ notifications: v })}
        />
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="newsletter">Newsletter</Label>
        <Switch
          id="newsletter"
          checked={data.newsletter}
          onCheckedChange={(v) => updateData({ newsletter: v })}
        />
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
        <Button onClick={() => setStep(3)}>Next</Button>
      </div>
    </div>
  );
}

function StepConfirmation() {
  const { data, setStep, reset } = useWizardStore();
  const handleSubmit = async () => {
    await fetch("/api/onboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    reset();
  };
  return (
    <div className="space-y-4">
      <div className="rounded-md border p-4 space-y-2 text-sm">
        <p><strong>Name:</strong> {data.name}</p>
        <p><strong>Email:</strong> {data.email}</p>
        <p><strong>Company:</strong> {data.company}</p>
        <p><strong>Plan:</strong> {data.plan}</p>
        <p><strong>Notifications:</strong> {data.notifications ? "Yes" : "No"}</p>
        <p><strong>Newsletter:</strong> {data.newsletter ? "Yes" : "No"}</p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
        <Button onClick={handleSubmit}>Submit</Button>
      </div>
    </div>
  );
}

export function FormWizard() {
  const step = useWizardStore((s) => s.step);
  return (
    <div className="max-w-md mx-auto">
      <StepIndicator />
      {step === 1 && <StepDetails />}
      {step === 2 && <StepPreferences />}
      {step === 3 && <StepConfirmation />}
    </div>
  );
}
```

## Dashboard Layout

Sidebar navigation with header and main content area, using Sheet for mobile sidebar toggle.

```tsx
// components/dashboard-layout.tsx
"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  FolderOpen,
  Users,
  Settings,
  Menu,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderOpen },
  { href: "/team", label: "Team", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

function NavLinks({ onClick }: { onClick?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="space-y-1">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          onClick={onClick}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            pathname === item.href
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <item.icon className="h-4 w-4" />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <div className="flex h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r p-4">
        <h2 className="text-lg font-semibold mb-6 px-3">My App</h2>
        <NavLinks />
      </aside>

      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex h-14 items-center gap-4 border-b px-4">
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-4">
              <h2 className="text-lg font-semibold mb-6 px-3">My App</h2>
              <NavLinks onClick={() => setSheetOpen(false)} />
            </SheetContent>
          </Sheet>
          <div className="flex-1" />
          <span className="text-sm text-muted-foreground">
            Press{" "}
            <kbd className="rounded border px-1.5 py-0.5 text-xs font-mono">
              Cmd+K
            </kbd>
          </span>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

## Toast Notifications

useToast hook pattern with success, error, and loading variants.

```tsx
// lib/use-app-toast.ts
import { useToast } from "@/components/ui/use-toast";

export function useAppToast() {
  const { toast } = useToast();

  return {
    success: (message: string) =>
      toast({ title: "Success", description: message }),

    error: (message: string) =>
      toast({ title: "Error", description: message, variant: "destructive" }),

    loading: (message: string) =>
      toast({ title: "Loading", description: message, duration: Infinity }),

    promise: async <T,>(
      promise: Promise<T>,
      msgs: { loading: string; success: string; error: string }
    ): Promise<T> => {
      const { dismiss } = toast({
        title: "Loading",
        description: msgs.loading,
        duration: Infinity,
      });
      try {
        const result = await promise;
        dismiss();
        toast({ title: "Success", description: msgs.success });
        return result;
      } catch (err) {
        dismiss();
        toast({ title: "Error", description: msgs.error, variant: "destructive" });
        throw err;
      }
    },
  };
}
```

Usage:

```tsx
const t = useAppToast();

// Simple notifications
t.success("Project created");
t.error("Something went wrong");

// Promise-based: shows loading, then success or error automatically
await t.promise(createProject(data), {
  loading: "Creating project...",
  success: "Project created!",
  error: "Failed to create project",
});
```

## Loading States

Suspense boundaries with skeleton loaders for the data table and dashboard.

```tsx
// components/skeletons.tsx
import { Skeleton } from "@/components/ui/skeleton";

export function DataTableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-64" /> {/* search bar */}
      <div className="rounded-md border">
        <div className="border-b p-4">
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, i) => (
              <Skeleton key={i} className="h-4 flex-1" />
            ))}
          </div>
        </div>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 p-4 border-b last:border-0">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
      <div className="flex justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-48" />
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-8 w-48" />
      <DataTableSkeleton />
    </div>
  );
}
```

Wrap pages in Suspense to show skeletons while data loads:

```tsx
// app/dashboard/page.tsx
import { Suspense } from "react";
import { DashboardSkeleton } from "@/components/skeletons";
import { DashboardContent } from "./dashboard-content";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardContent />
    </Suspense>
  );
}
```
