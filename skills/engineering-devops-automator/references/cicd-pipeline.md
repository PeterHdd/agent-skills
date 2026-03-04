# CI/CD Pipeline

## GitHub Actions with Blue-Green Deploy

Full pipeline with security scanning, testing, container build, and blue-green deployment with smoke tests.

```yaml
# GitHub Actions Pipeline with security scanning and container build
name: Production Deployment

on:
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Dependency vulnerability scan
        run: npm audit --audit-level high
      - name: Container security scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  test:
    needs: security-scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          npm ci
          npm test
          npm run test:integration

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push container
        run: |
          docker build -t registry/app:${{ github.sha }} .
          docker push registry/app:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Blue-Green Deploy
        run: |
          CURRENT=$(kubectl get svc app -o jsonpath='{.spec.selector.slot}')
          if [ "$CURRENT" = "blue" ]; then TARGET="green"; else TARGET="blue"; fi

          # Deploy new version to the inactive slot
          kubectl set image deployment/app-$TARGET app=registry/app:${{ github.sha }}
          kubectl rollout status deployment/app-$TARGET --timeout=300s

          # Smoke test the inactive slot via its internal service
          kubectl run smoke-test --rm -i --restart=Never \
            --image=curlimages/curl -- \
            curl -sf http://app-$TARGET:8080/health/ready

          # Switch production traffic to the new slot
          kubectl patch svc app -p "{\"spec\":{\"selector\":{\"slot\":\"$TARGET\"}}}"

          echo "Traffic switched from $CURRENT to $TARGET"
```
