# Test Suite

## Vitest + Fetch Test Suite

```typescript
import { describe, test, expect, beforeAll } from 'vitest';
import { performance } from 'perf_hooks';

describe('User API Comprehensive Testing', () => {
  let authToken: string;
  const baseURL = process.env.API_BASE_URL ?? 'http://localhost:3000';

  beforeAll(async () => {
    const response = await fetch(`${baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'secure_password' })
    });
    authToken = (await response.json()).token;
  });

  describe('Functional Testing', () => {
    test('should create user with valid data', async () => {
      const response = await fetch(`${baseURL}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ name: 'Test User', email: 'new@example.com', role: 'user' })
      });
      expect(response.status).toBe(201);
      const user = await response.json();
      expect(user.password).toBeUndefined();
    });

    test('should handle invalid input gracefully', async () => {
      const response = await fetch(`${baseURL}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ name: '', email: 'invalid-email', role: 'invalid_role' })
      });
      expect(response.status).toBe(400);
      expect((await response.json()).errors).toContain('Invalid email format');
    });
  });

  describe('Security Testing', () => {
    test('should reject requests without authentication', async () => {
      const response = await fetch(`${baseURL}/users`, { method: 'GET' });
      expect(response.status).toBe(401);
    });

    test('should prevent SQL injection via query parameters', async () => {
      const maliciousInput = encodeURIComponent("' OR 1=1; --");
      const response = await fetch(`${baseURL}/users?search=${maliciousInput}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      // Server must not crash (no 500) and must not return all rows
      expect(response.status).not.toBe(500);
      const body = await response.json();
      // A properly parameterized query returns zero results for this literal string
      expect(Array.isArray(body.data) ? body.data.length : 0).toBeLessThanOrEqual(1);
    });

    test('should enforce rate limiting', async () => {
      const requests = Array.from({ length: 100 }, () =>
        fetch(`${baseURL}/users`, { headers: { 'Authorization': `Bearer ${authToken}` } })
      );
      const responses = await Promise.all(requests);
      expect(responses.some(r => r.status === 429)).toBe(true);
    });
  });

  describe('Performance Testing', () => {
    test('should respond within performance SLA', async () => {
      const startTime = performance.now();
      const response = await fetch(`${baseURL}/users`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      expect(response.status).toBe(200);
      expect(performance.now() - startTime).toBeLessThan(200);
    });

    test('should handle concurrent requests efficiently', async () => {
      const startTime = performance.now();
      const responses = await Promise.all(
        Array.from({ length: 50 }, () =>
          fetch(`${baseURL}/users`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        )
      );
      expect(responses.every(r => r.status === 200)).toBe(true);
      expect((performance.now() - startTime) / 50).toBeLessThan(500);
    });
  });
});
```
