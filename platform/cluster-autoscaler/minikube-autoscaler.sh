#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME=${CLUSTER_NAME:-carsharing}
MIN_WORKERS=${MIN_WORKERS:-0}
MAX_WORKERS=${MAX_WORKERS:-3}
POLL_SECONDS=${POLL_SECONDS:-10}
SCALE_UP_COOLDOWN_SECONDS=${SCALE_UP_COOLDOWN_SECONDS:-60}

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "$1 not found"; exit 1; }
}

require kubectl
require minikube

last_scale_up=0

worker_count() {
  kubectl get nodes -l autoscaling.carsharing/local=true --no-headers 2>/dev/null | wc -l | tr -d ' '
}

pending_pods() {
  kubectl get pods -A --field-selector=status.phase=Pending --no-headers 2>/dev/null | wc -l | tr -d ' '
}

label_workers() {
  kubectl get nodes -o name | while read -r node; do
    if [[ "${node}" != "node/${CLUSTER_NAME}" ]]; then
      kubectl label "${node}" \
        node-role=worker \
        workload=carsharing \
        autoscaling.carsharing/local=true \
        --overwrite >/dev/null
    fi
  done
}

echo "local Cluster Autoscaler for Minikube"
echo "cluster=${CLUSTER_NAME} minWorkers=${MIN_WORKERS} maxWorkers=${MAX_WORKERS}"
echo "watching Pending pods; press Ctrl+C to stop"

label_workers

while true; do
  pending=$(pending_pods)
  workers=$(worker_count)
  now=$(date +%s)

  echo "$(date '+%H:%M:%S') pendingPods=${pending} localWorkers=${workers}/${MAX_WORKERS}"

  if [[ "${workers}" -lt "${MIN_WORKERS}" ]]; then
    echo "bootstrap: localWorkers=${workers} is below MIN_WORKERS=${MIN_WORKERS}; adding a worker node"
    minikube node add -p "${CLUSTER_NAME}" --worker
    label_workers
    kubectl wait --for=condition=Ready node --all --timeout=5m
    last_scale_up=$(date +%s)
  elif [[ "${pending}" -gt 0 && "${workers}" -lt "${MAX_WORKERS}" ]]; then
    if (( now - last_scale_up >= SCALE_UP_COOLDOWN_SECONDS )); then
      echo "scale-up: ${pending} pods are Pending; adding a Minikube worker node"
      minikube node add -p "${CLUSTER_NAME}" --worker
      label_workers
      kubectl wait --for=condition=Ready node --all --timeout=5m
      last_scale_up=$(date +%s)
    else
      echo "scale-up skipped: cooldown is active"
    fi
  fi

  sleep "${POLL_SECONDS}"
done
