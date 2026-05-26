#!/usr/bin/env bash
set -euo pipefail

ARGOCD_VERSION=${ARGOCD_VERSION:-7.6.12}

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm repo update >/dev/null

helm upgrade --install argocd argo/argo-cd \
  --version "${ARGOCD_VERSION}" \
  --namespace argocd \
  --values "$(dirname "$0")/argocd-values.yaml" \
  --wait --timeout 10m

kubectl apply -f "$(dirname "$0")/root-app.yaml"
kubectl -n argocd wait --for=condition=Available deploy/argocd-server --timeout=5m
kubectl -n argocd get applications.argoproj.io
