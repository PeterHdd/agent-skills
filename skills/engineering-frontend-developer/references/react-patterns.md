# React Component Patterns (React 18+ / TypeScript)

Production-ready patterns for modern React applications.

---

## Compound Component Pattern — Tabs

Uses React context to share state between parent and child components without prop drilling.

```tsx
import React, { createContext, useContext, useState, ReactNode } from 'react';

interface TabsContextValue {
  activeIndex: number;
  setActiveIndex: (index: number) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('Tabs compound components must be used within <Tabs>');
  return ctx;
}

function Tabs({ defaultIndex = 0, children }: { defaultIndex?: number; children: ReactNode }) {
  const [activeIndex, setActiveIndex] = useState(defaultIndex);
  return (
    <TabsContext.Provider value={{ activeIndex, setActiveIndex }}>
      <div role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

function TabList({ children }: { children: ReactNode }) {
  return <div role="tablist" className="flex border-b">{children}</div>;
}

function Tab({ index, children }: { index: number; children: ReactNode }) {
  const { activeIndex, setActiveIndex } = useTabsContext();
  return (
    <button
      role="tab"
      aria-selected={activeIndex === index}
      onClick={() => setActiveIndex(index)}
      className={activeIndex === index ? 'border-b-2 border-blue-600 font-semibold' : ''}
    >
      {children}
    </button>
  );
}

function Panel({ index, children }: { index: number; children: ReactNode }) {
  const { activeIndex } = useTabsContext();
  if (activeIndex !== index) return null;
  return <div role="tabpanel">{children}</div>;
}

Tabs.List = TabList;
Tabs.Tab = Tab;
Tabs.Panel = Panel;

export { Tabs };
```

Usage:

```tsx
<Tabs defaultIndex={0}>
  <Tabs.List>
    <Tabs.Tab index={0}>Profile</Tabs.Tab>
    <Tabs.Tab index={1}>Settings</Tabs.Tab>
  </Tabs.List>
  <Tabs.Panel index={0}>Profile content here</Tabs.Panel>
  <Tabs.Panel index={1}>Settings content here</Tabs.Panel>
</Tabs>
```

---

## Custom Hook — useDebounce

Debounces a rapidly changing value. Cleans up the timer on unmount or when value/delay changes.

```tsx
import { useState, useEffect } from 'react';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

export { useDebounce };
```

Usage:

```tsx
function SearchInput() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) fetchResults(debouncedQuery);
  }, [debouncedQuery]);

  return <input value={query} onChange={(e) => setQuery(e.target.value)} />;
}
```

---

## Custom Hook — useFetch

Generic data-fetching hook with loading, error, and data states. Uses AbortController to cancel in-flight requests on cleanup.

```tsx
import { useState, useEffect } from 'react';

interface FetchState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
}

function useFetch<T>(url: string): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    error: null,
    isLoading: true,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, error: null, isLoading: true });

    fetch(url, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.json() as Promise<T>;
      })
      .then((data) => setState({ data, error: null, isLoading: false }))
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setState({ data: null, error: err, isLoading: false });
        }
      });

    return () => controller.abort();
  }, [url]);

  return state;
}

export { useFetch };
```

Usage:

```tsx
interface User { id: string; name: string; email: string }

function UserProfile({ userId }: { userId: string }) {
  const { data, error, isLoading } = useFetch<User>(`/api/users/${userId}`);

  if (isLoading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  return <div>{data?.name}</div>;
}
```

---

## Error Boundary with Fallback UI and Retry

Class component (required for error boundaries) with a retry mechanism.

```tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) return this.props.fallback(error, this.handleRetry);
      return (
        <div role="alert" className="p-4 border border-red-300 rounded bg-red-50">
          <h2 className="font-semibold text-red-800">Something went wrong</h2>
          <p className="text-red-600 text-sm">{error.message}</p>
          <button onClick={this.handleRetry} className="mt-2 px-3 py-1 bg-red-600 text-white rounded">
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export { ErrorBoundary };
```

Usage:

```tsx
<ErrorBoundary fallback={(err, retry) => (
  <div>
    <p>Failed: {err.message}</p>
    <button onClick={retry}>Retry</button>
  </div>
)}>
  <Dashboard />
</ErrorBoundary>
```

---

## Optimistic UI Update with Rollback

Shows immediate UI feedback while the server request is in flight, rolling back on failure.

```tsx
import { useState } from 'react';

interface Todo { id: string; text: string; done: boolean }

function useTodoToggle(initialTodos: Todo[]) {
  const [todos, setTodos] = useState(initialTodos);

  async function toggleTodo(id: string) {
    const previous = todos;

    // Optimistic update
    setTodos((current) =>
      current.map((t) => (t.id === id ? { ...t, done: !t.done } : t))
    );

    try {
      const todo = previous.find((t) => t.id === id)!;
      const res = await fetch(`/api/todos/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: !todo.done }),
      });
      if (!res.ok) throw new Error('Update failed');
    } catch {
      // Rollback to previous state
      setTodos(previous);
    }
  }

  return { todos, toggleTodo };
}

export { useTodoToggle };
```

Usage:

```tsx
function TodoList({ initialTodos }: { initialTodos: Todo[] }) {
  const { todos, toggleTodo } = useTodoToggle(initialTodos);

  return (
    <ul>
      {todos.map((t) => (
        <li key={t.id}>
          <label>
            <input type="checkbox" checked={t.done} onChange={() => toggleTodo(t.id)} />
            <span className={t.done ? 'line-through' : ''}>{t.text}</span>
          </label>
        </li>
      ))}
    </ul>
  );
}
```

---

## Form with react-hook-form + zod Validation

Type-safe form validation using zod schemas with react-hook-form.

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const signupSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

type SignupFormData = z.infer<typeof signupSchema>;
```

```tsx
function SignupForm({ onSubmit }: { onSubmit: (data: SignupFormData) => Promise<void> }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" {...register('email')} aria-describedby="email-error" />
        {errors.email && <p id="email-error" role="alert">{errors.email.message}</p>}
      </div>
      <div>
        <label htmlFor="password">Password</label>
        <input id="password" type="password" {...register('password')} aria-describedby="pw-error" />
        {errors.password && <p id="pw-error" role="alert">{errors.password.message}</p>}
      </div>
      <div>
        <label htmlFor="confirmPassword">Confirm Password</label>
        <input id="confirmPassword" type="password" {...register('confirmPassword')} aria-describedby="cpw-error" />
        {errors.confirmPassword && <p id="cpw-error" role="alert">{errors.confirmPassword.message}</p>}
      </div>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Signing up...' : 'Sign Up'}
      </button>
    </form>
  );
}

export { SignupForm, signupSchema };
```

---

## Render Prop vs Hook — Comparison

The same "toggle" feature implemented both ways, showing how hooks supersede render props for most cases.

### Render Prop Pattern (legacy)

```tsx
import { useState, ReactNode } from 'react';

interface ToggleRenderProps {
  isOn: boolean;
  toggle: () => void;
}

function Toggle({ children }: { children: (props: ToggleRenderProps) => ReactNode }) {
  const [isOn, setIsOn] = useState(false);
  return <>{children({ isOn, toggle: () => setIsOn((prev) => !prev) })}</>;
}

// Usage
<Toggle>
  {({ isOn, toggle }) => (
    <button onClick={toggle}>{isOn ? 'ON' : 'OFF'}</button>
  )}
</Toggle>
```

### Hook Pattern (preferred)

```tsx
import { useState, useCallback } from 'react';

function useToggle(initial = false) {
  const [isOn, setIsOn] = useState(initial);
  const toggle = useCallback(() => setIsOn((prev) => !prev), []);
  return { isOn, toggle } as const;
}

// Usage
function ToggleButton() {
  const { isOn, toggle } = useToggle();
  return <button onClick={toggle}>{isOn ? 'ON' : 'OFF'}</button>;
}

export { useToggle };
```

The hook pattern is preferred because it avoids the nested callback JSX, is easier to compose (call multiple hooks in one component), and produces simpler component trees in React DevTools. Use render props only when you need to share behavior with class components or need inversion of control over rendering.
