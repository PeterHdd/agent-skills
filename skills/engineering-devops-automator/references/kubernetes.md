# Kubernetes Patterns

## Production Deployment

Deployment with resource limits, health probes, rolling update strategy, and pod anti-affinity for high availability.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: production
  labels:
    app: app
    version: v1
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
        version: v1
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values: [app]
                topologyKey: kubernetes.io/hostname
      containers:
        - name: app
          image: registry.example.com/app:1.4.2
          ports:
            - containerPort: 8080
              protocol: TCP
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
            failureThreshold: 3
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
```

## Horizontal Pod Autoscaler

HPA targeting CPU utilization and a custom metric for request throughput.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 20
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
```

## PodDisruptionBudget

Ensures at least one pod remains available during voluntary disruptions such as node drains or cluster upgrades.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: production
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: app
```

## ConfigMap and Secret Mounting

ConfigMap for application configuration and Secret for credentials, both exposed as environment variables and mounted as files.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  LOG_LEVEL: "info"
  NODE_ENV: "production"
  CACHE_TTL: "300"
  app.conf: |
    server.port=8080
    server.graceful-shutdown=30s
    feature.dark-mode=true
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
type: Opaque
stringData:
  DATABASE_URL: "postgresql://example_user:example_pass@db.example.invalid:5432/appdb"
  API_KEY: "example_api_key_not_real"
  credentials.json: |
    {"client_id":"example_client_id","client_secret":"example_client_secret"}
---
# Pod spec snippet showing both env var and volume mount usage
apiVersion: v1
kind: Pod
metadata:
  name: app-pod-example
spec:
  containers:
    - name: app
      image: registry.example.com/app:1.4.2
      envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
      volumeMounts:
        - name: config-volume
          mountPath: /etc/app/config
          readOnly: true
        - name: secret-volume
          mountPath: /etc/app/secrets
          readOnly: true
  volumes:
    - name: config-volume
      configMap:
        name: app-config
        items:
          - key: app.conf
            path: app.conf
    - name: secret-volume
      secret:
        secretName: app-secrets
        items:
          - key: credentials.json
            path: credentials.json
```

## Ingress with TLS

Nginx ingress with cert-manager for automatic TLS certificate provisioning, rate limiting, and path-based routing.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls-cert
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
          - path: /ws
            pathType: Prefix
            backend:
              service:
                name: websocket-service
                port:
                  number: 8081
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 3000
```

## CronJob

Database backup CronJob running daily at 2 AM UTC with concurrency protection and retry limits.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
  namespace: production
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 3
      activeDeadlineSeconds: 3600
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: backup
              image: registry.example.com/db-backup:2.1.0
              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: app-secrets
                      key: DATABASE_URL
                - name: S3_BUCKET
                  value: "my-app-backups"
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump "$DATABASE_URL" | gzip > /tmp/backup-$(date +%Y%m%d).sql.gz
                  aws s3 cp /tmp/backup-$(date +%Y%m%d).sql.gz "s3://$S3_BUCKET/$(date +%Y/%m)/"
```

## Helm values.yaml

Production values file serving as a template for any Helm-based application deployment.

```yaml
# values-production.yaml
replicaCount: 3

image:
  repository: registry.example.com/app
  tag: "1.4.2"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: "1"
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: app-tls-cert
      hosts:
        - app.example.com

env:
  LOG_LEVEL: "info"
  NODE_ENV: "production"
  CACHE_TTL: "300"

secrets:
  DATABASE_URL: "vault:kv/data/app#DATABASE_URL"

probes:
  readiness:
    path: /health/ready
    initialDelaySeconds: 5
  liveness:
    path: /health/live
    initialDelaySeconds: 15
```
