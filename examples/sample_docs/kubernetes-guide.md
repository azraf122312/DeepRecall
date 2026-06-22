# Kubernetes Operations Guide

## 4.1 Autoscaling Overview

Autoscaling lets a Deployment grow and shrink automatically with load. In
Kubernetes the Horizontal Pod Autoscaler (HPA) is the primary mechanism. It
adjusts the number of Pod replicas based on observed CPU, memory, or custom
metrics.

## 4.2 HPA Configuration

To configure auto-scaling for a workload such as the API Gateway:

1. Ensure the metrics-server is installed and healthy in the cluster.
2. Add resource requests to the Deployment so HPA has a baseline.
3. Create an HPA object targeting the Deployment.
4. Set minReplicas, maxReplicas, and a target CPU utilization.
5. Apply the manifest and watch `kubectl get hpa` during traffic.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## 4.3 Prerequisites

The metrics-server is a hard prerequisite for HPA. Without it, the HPA
reports `unknown` for metrics and never scales. Install it before creating
any HorizontalPodAutoscaler.

## 4.4 Common Misconfigurations

Warning: never set minReplicas to 0 for a public API Gateway. Doing so lets
the service scale to zero Pods during a lull, causing cold-start latency or
outright downtime when traffic returns. Avoid omitting resource requests —
HPA cannot compute utilization without them.
