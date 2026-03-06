# Auth Patterns

Use this when reviewing login, session, token, or permission changes.

## Core Checks

- Authentication proves identity. Authorization proves allowed action. Never merge them mentally.
- Check where tokens or sessions are created, validated, rotated, and revoked.
- Check whether authorization runs on every protected endpoint, not only at the edge.

## Common Failure Modes

- JWT validated but role or tenant scope never checked.
- Session cookie missing `HttpOnly`, `Secure`, or `SameSite`.
- Refresh token rotation missing replay protection.
