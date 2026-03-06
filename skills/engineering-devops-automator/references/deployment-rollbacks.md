# Deployment Rollback Guide

Use this when a change is risky, user-facing, or modifies runtime behavior in production.

## Rollback Types

### Stateless Service Rollback
- Revert image tag or release version.
- Confirm readiness probes pass on the previous version.
- Verify logs and latency normalize within one deploy window.

### Canary Rollback
- Shift traffic back to stable immediately when error rate or latency breaches the canary gate.
- Do not continue diagnosing on 50% traffic if the gate already failed at 5-10%.

### Blue-Green Rollback
- Move the load balancer or router back to the previous environment.
- Keep the failed environment intact for investigation until evidence is collected.

### Schema-Aware Rollback
- If the migration is backward compatible, roll back code first.
- If the migration dropped or rewrote data, do not roll back blindly. Switch to mitigation mode and verify restore options.

## Preconditions Before Any Risky Deploy

- Health checks cover startup and dependency readiness.
- Metrics exist for error rate and latency on the changed path.
- Rollback command or UI action is known before rollout starts.
- State changes are classified: reversible, forward-only, or destructive.
