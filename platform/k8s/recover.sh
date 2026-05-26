#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME=${CLUSTER_NAME:-carsharing}
CILIUM_VERSION=${CILIUM_VERSION:-1.16.3}

KUBECTL() { minikube -p "${CLUSTER_NAME}" kubectl -- "$@"; }

helm uninstall cilium -n kube-system 2>/dev/null || true

KUBECTL -n kube-system delete ds cilium-envoy --ignore-not-found
KUBECTL -n kube-system delete ds cilium --ignore-not-found
KUBECTL -n kube-system delete deploy cilium-operator hubble-relay hubble-ui --ignore-not-found
KUBECTL -n kube-system delete pod -l k8s-app=cilium --grace-period=0 --force 2>/dev/null || true
KUBECTL -n kube-system delete pod -l k8s-app=cilium-envoy --grace-period=0 --force 2>/dev/null || true

docker pull "quay.io/cilium/cilium:v${CILIUM_VERSION}" || true
docker pull "quay.io/cilium/operator-generic:v${CILIUM_VERSION}" || true
minikube -p "${CLUSTER_NAME}" image load "quay.io/cilium/cilium:v${CILIUM_VERSION}" 2>/dev/null || true
minikube -p "${CLUSTER_NAME}" image load "quay.io/cilium/operator-generic:v${CILIUM_VERSION}" 2>/dev/null || true

helm repo add cilium https://helm.cilium.io/ >/dev/null 2>&1 || true
helm repo update >/dev/null

API_SERVER_HOST=$(minikube ip -p "${CLUSTER_NAME}")

helm upgrade --install cilium cilium/cilium \
  --version "${CILIUM_VERSION}" \
  --namespace kube-system \
  --values "$(dirname "$0")/cilium-values.yaml" \
  --set k8sServiceHost="${API_SERVER_HOST}" \
  --set k8sServicePort=8443

sleep 10
KUBECTL -n kube-system wait --for=condition=Ready pod -l k8s-app=cilium --timeout=5m
KUBECTL -n kube-system wait --for=condition=Available deploy/cilium-operator --timeout=5m

KUBECTL -n kube-system rollout restart deploy/coredns
KUBECTL -n kube-system wait --for=condition=Available deploy/coredns --timeout=3m

KUBECTL get nodes -o wide
KUBECTL -n kube-system get pods
