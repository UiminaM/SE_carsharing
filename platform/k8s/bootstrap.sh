#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME=${CLUSTER_NAME:-carsharing}
K8S_VERSION=${K8S_VERSION:-v1.30.0}
NODES=${NODES:-1}
CPUS=${CPUS:-4}
MEMORY=${MEMORY:-8192}
CNI=${CNI:-cilium}
CILIUM_VERSION=${CILIUM_VERSION:-1.16.3}

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "$1 not found"; exit 1; }
}

KUBECTL() {
  minikube -p "${CLUSTER_NAME}" kubectl -- "$@"
}

retry() {
  local n=0
  local max=${1:?max retries}
  shift
  local delay=2
  until "$@"; do
    n=$((n+1))
    if [[ $n -ge $max ]]; then
      return 1
    fi
    sleep "$delay"
    delay=$((delay*2))
    [[ $delay -gt 20 ]] && delay=20
  done
}

require minikube
require kubectl
require helm
require docker

minikube delete -p "${CLUSTER_NAME}" || true

case "${CNI}" in
  cilium)   MK_CNI_FLAG="--cni=false" ;;
  flannel)  MK_CNI_FLAG="--cni=flannel" ;;
  kindnet)  MK_CNI_FLAG="--cni=kindnet" ;;
  *) echo "unknown CNI=${CNI}"; exit 1 ;;
esac

minikube start \
  -p "${CLUSTER_NAME}" \
  --kubernetes-version="${K8S_VERSION}" \
  --nodes="${NODES}" \
  --cpus="${CPUS}" \
  --memory="${MEMORY}" \
  ${MK_CNI_FLAG}

kubectl config use-context "${CLUSTER_NAME}"

KUBECTL get nodes -o name | tail -n +2 | while read -r n; do
  KUBECTL label "$n" node-role=worker --overwrite
done

retry 12 KUBECTL get --raw='/readyz?verbose'

if [[ "${CNI}" == "cilium" ]]; then
  if docker pull "quay.io/cilium/cilium:v${CILIUM_VERSION}" 2>/dev/null && \
     docker pull "quay.io/cilium/operator-generic:v${CILIUM_VERSION}" 2>/dev/null; then
    minikube -p "${CLUSTER_NAME}" image load "quay.io/cilium/cilium:v${CILIUM_VERSION}"
    minikube -p "${CLUSTER_NAME}" image load "quay.io/cilium/operator-generic:v${CILIUM_VERSION}"
  fi

  helm repo add cilium https://helm.cilium.io/ >/dev/null 2>&1 || true
  helm repo update >/dev/null

  API_SERVER_HOST=$(minikube ip -p "${CLUSTER_NAME}")
  API_SERVER_PORT=8443

  helm upgrade --install cilium cilium/cilium \
    --version "${CILIUM_VERSION}" \
    --namespace kube-system \
    --values "$(dirname "$0")/cilium-values.yaml" \
    --set k8sServiceHost="${API_SERVER_HOST}" \
    --set k8sServicePort="${API_SERVER_PORT}"

  sleep 10
  retry 10 KUBECTL -n kube-system wait --for=condition=Ready pod -l k8s-app=cilium --timeout=5m
  retry 10 KUBECTL -n kube-system wait --for=condition=Available deploy/cilium-operator --timeout=5m
else
  retry 10 KUBECTL -n kube-system wait --for=condition=Ready pod --all --timeout=3m || true
fi

minikube addons enable metrics-server -p "${CLUSTER_NAME}" || true

KUBECTL get nodes -o wide
KUBECTL -n kube-system get pods
