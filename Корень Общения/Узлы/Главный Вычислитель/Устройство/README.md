# rust-inference

Самодостаточный узел тяжёлого инференса для цепочки `user-message-processing`.

## Локальный запуск (Rust)

```bash
cargo run
```

HTTP endpoints:
- `GET /health`
- `POST /infer` with JSON `{"prompt":"..."}`.

## Docker Compose

```bash
docker compose -f docker-compose.inference.yml up --build -d
curl http://localhost:8081/health
curl -X POST http://localhost:8081/infer \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Привет, узел!"}'
```

Остановка:

```bash
docker compose -f docker-compose.inference.yml down
```

## Kubernetes

1) Собери и запушь образ:

```bash
docker build -t yourregistry/rust-inference:latest .
docker push yourregistry/rust-inference:latest
```

2) Примени манифесты:

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

3) Быстрая проверка:

```bash
kubectl port-forward svc/rust-inference 8081:8081
curl http://localhost:8081/health
```

## Тесты

```bash
cargo test
```
