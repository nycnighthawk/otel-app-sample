# Testing each component on the Linux VM (Ubuntu)

## 0) One-time: prepare the DB volume (schema + seed)
```bash
bash podman/db-build.sh
# optional bigger:
# SEED_ROWS=100000 bash podman/db-build.sh
```

## 1) Start DB
```bash
bash podman/db-run.sh
```

## 2) Start Tempo (traces backend)
```bash
bash podman/tempo-run.sh
```

## 3) Start OTel Collector
```bash
bash podman/otelcol-run.sh
```

## 4) Start Prometheus
```bash
bash podman/prometheus-run.sh
```

## 5) Start Grafana
```bash
bash podman/grafana-run.sh
```

## 6) Start Python app (container)
Build the image first:
```bash
bash podman/build.sh
```

Run it:
```bash
bash podman/app-run.sh
```

Open:
- http://localhost:8080

## 7) Start Java app (jar) on Linux VM
Build jar using containerized Maven:
```bash
bash java-app/build-container.sh
```

Run:
```bash
bash java-app/run-linux.sh
```

Open:
- http://localhost:8081

## 8) Smoke test everything
```bash
bash podman/stack-test.sh
```
