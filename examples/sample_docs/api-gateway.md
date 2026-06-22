# API Gateway Reference

## 3.1 Traffic Patterns

The API Gateway sits at the edge and absorbs spikes in incoming traffic.
During high traffic events the gateway must scale horizontally to keep
latency within SLO. It depends on the Load Balancer in front and the
Kubernetes HPA behind it.

## 3.2 Auto-scaling the Gateway

To handle high traffic, the API Gateway should auto-scale on both CPU and
request-rate metrics. Configure the HPA to target 70% CPU utilization and add
a custom requests-per-second metric for sharper response. Pair this with a
Load Balancer that spreads connections evenly across replicas.

## 3.3 Rate Limiting vs Auto-scaling

Choosing between rate limiting and auto-scaling is a trade-off. Rate limiting
protects downstream services but rejects users; auto-scaling preserves
availability but costs more. Most teams combine both: auto-scale first, then
rate-limit as a backstop.

| Strategy       | Protects | User impact | Cost   |
|----------------|----------|-------------|--------|
| Auto-scaling   | Latency  | Low         | Higher |
| Rate limiting  | Backend  | Rejections  | Lower  |
