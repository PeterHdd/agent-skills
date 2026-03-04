# TypeScript Patterns for Frontend

Production-ready TypeScript patterns for React and frontend applications.

---

## Discriminated Union for Async State

Model every possible state of an async operation as a tagged union. This eliminates impossible states (e.g., `isLoading: true` and `error` being set simultaneously).

```ts
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function renderState<T>(state: AsyncState<T>, render: (data: T) => React.ReactNode) {
  switch (state.status) {
    case 'idle':
      return null;
    case 'loading':
      return <Spinner />;
    case 'success':
      return render(state.data); // `data` is narrowed here
    case 'error':
      return <ErrorMessage message={state.error.message} />;
  }
}
```

---

## Polymorphic Component with `as` Prop

Allows a component to render as any HTML element or React component while preserving type safety for the rendered element's props.

```tsx
import React, { ElementType, ComponentPropsWithoutRef, ReactNode } from 'react';

type PolymorphicProps<E extends ElementType> = {
  as?: E;
  children: ReactNode;
} & Omit<ComponentPropsWithoutRef<E>, 'as' | 'children'>;

function Text<E extends ElementType = 'span'>({ as, children, ...props }: PolymorphicProps<E>) {
  const Component = as ?? 'span';
  return <Component {...props}>{children}</Component>;
}

export { Text };
```

Usage -- the `href` prop is type-checked because `as="a"` narrows the allowed props to anchor attributes:

```tsx
<Text as="a" href="/about" className="text-blue-600">About</Text>
<Text as="h1" className="text-3xl font-bold">Title</Text>
<Text>Defaults to a span element</Text>
```

---

## Strict Event Handler Typing

Always use React's synthetic event types for handlers. This ensures the handler receives the correct `currentTarget` and prevents mixing up event sources.

```tsx
import React from 'react';

// Text input change
function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
  const value: string = e.currentTarget.value;
  console.log(value);
}

// Select element change
function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
  const selected: string = e.currentTarget.value;
  console.log(selected);
}

// Keyboard event with key filtering
function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
  if (e.key === 'Escape') {
    e.currentTarget.blur();
  }
}

// Form submission
function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
  e.preventDefault();
  const formData = new FormData(e.currentTarget);
  console.log(Object.fromEntries(formData));
}

// Mouse event with coordinates
function handleClick(e: React.MouseEvent<HTMLButtonElement>) {
  console.log(`Clicked at (${e.clientX}, ${e.clientY})`);
}
```

---

## Type-Safe Route Params with Const Assertions

Define route paths as constants and derive param types from them, preventing typos and keeping routes in sync.

```ts
const ROUTES = {
  home: '/',
  userProfile: '/users/:userId',
  orderDetail: '/orders/:orderId/items/:itemId',
  settings: '/settings',
} as const;

type RouteKey = keyof typeof ROUTES;

// Extract param names from a route pattern
type ExtractParams<T extends string> =
  T extends `${string}:${infer Param}/${infer Rest}`
    ? Param | ExtractParams<Rest>
    : T extends `${string}:${infer Param}`
      ? Param
      : never;

// Build a params object for a given route
type RouteParams<K extends RouteKey> = {
  [P in ExtractParams<(typeof ROUTES)[K]>]: string;
};

// Type-safe path builder
function buildPath<K extends RouteKey>(
  route: K,
  ...args: ExtractParams<(typeof ROUTES)[K]> extends never
    ? []
    : [params: RouteParams<K>]
): string {
  const params = args[0] as Record<string, string> | undefined;
  let path: string = ROUTES[route];
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      path = path.replace(`:${key}`, encodeURIComponent(value));
    }
  }
  return path;
}
```

Usage:

```ts
buildPath('home');                                         // "/"
buildPath('userProfile', { userId: '42' });                // "/users/42"
buildPath('orderDetail', { orderId: '7', itemId: '3' });   // "/orders/7/items/3"
// buildPath('userProfile');                                // Type error: missing params
// buildPath('userProfile', { orderId: '42' });             // Type error: wrong param name
```

---

## Utility Types Showcase

Each built-in utility type applied to a realistic frontend scenario.

```ts
interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl: string;
  role: 'admin' | 'editor' | 'viewer';
  preferences: { theme: 'light' | 'dark'; locale: string };
}

// Pick: extract only what a component needs
type UserCardProps = Pick<User, 'name' | 'avatarUrl' | 'role'>;

// Omit: everything except the server-generated field
type CreateUserPayload = Omit<User, 'id'>;

// Partial: for PATCH endpoints where every field is optional
type UpdateUserPayload = Partial<Omit<User, 'id'>>;

// Required: ensure optional fields are provided in admin forms
type AdminUserForm = Required<UpdateUserPayload>;

// Record: map known status codes to UI messages
type StatusMessages = Record<'success' | 'error' | 'pending', string>;
const messages: StatusMessages = {
  success: 'Operation completed.',
  error: 'Something went wrong.',
  pending: 'Processing your request...',
};

// Extract: narrow a union to specific members
type EditableRole = Extract<User['role'], 'editor' | 'viewer'>;
// Result: 'editor' | 'viewer'
```

---

## Type-Safe API Client with Generics

A thin typed wrapper around `fetch` that infers response types from an endpoint map.

```ts
interface ApiEndpoints {
  'GET /users': { response: User[]; params?: { role?: string } };
  'GET /users/:id': { response: User };
  'POST /users': { response: User; body: CreateUserPayload };
  'PATCH /users/:id': { response: User; body: UpdateUserPayload };
  'DELETE /users/:id': { response: void };
}

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE';

async function apiClient<K extends keyof ApiEndpoints>(
  endpoint: K,
  options?: {
    params?: Record<string, string>;
    body?: ApiEndpoints[K] extends { body: infer B } ? B : never;
  },
): Promise<ApiEndpoints[K]['response']> {
  const [method, pathTemplate] = (endpoint as string).split(' ') as [Method, string];

  let path = pathTemplate;
  if (options?.params) {
    for (const [key, value] of Object.entries(options.params)) {
      path = path.replace(`:${key}`, encodeURIComponent(value));
    }
  }

  const res = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: options?.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as ApiEndpoints[K]['response'];
  return res.json();
}
```

Usage -- return types are inferred automatically:

```ts
const users = await apiClient('GET /users');             // User[]
const user = await apiClient('GET /users/:id', {
  params: { id: '42' },
});                                                       // User
const created = await apiClient('POST /users', {
  body: { name: 'Ada', email: 'ada@example.com', avatarUrl: '', role: 'editor', preferences: { theme: 'light', locale: 'en' } },
});                                                       // User
```

---

## Branded Types for IDs

Prevents accidentally passing a `UserId` where an `OrderId` is expected, even though both are strings at runtime.

```ts
declare const __brand: unique symbol;

type Brand<T, B extends string> = T & { readonly [__brand]: B };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
type ProductId = Brand<string, 'ProductId'>;

// Constructor functions
function UserId(id: string): UserId { return id as UserId; }
function OrderId(id: string): OrderId { return id as OrderId; }
function ProductId(id: string): ProductId { return id as ProductId; }

// Type-safe functions
function fetchUser(id: UserId): Promise<User> {
  return apiClient('GET /users/:id', { params: { id } });
}

function fetchOrder(id: OrderId): Promise<Order> {
  return fetch(`/api/orders/${id}`).then((r) => r.json());
}

// Usage
const userId = UserId('usr_abc123');
const orderId = OrderId('ord_xyz789');

fetchUser(userId);    // OK
// fetchUser(orderId); // Type error: OrderId is not assignable to UserId
// fetchUser('raw');   // Type error: string is not assignable to UserId
```

This costs zero bytes at runtime (brands are erased during compilation) but catches ID mix-ups at compile time.
