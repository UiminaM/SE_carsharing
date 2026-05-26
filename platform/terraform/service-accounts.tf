locals {
  app_service_accounts = {
    "api-gateway"     = { namespace = "carsharing" }
    "car-service"     = { namespace = "carsharing" }
    "user-service"    = { namespace = "carsharing" }
    "trip-service"    = { namespace = "carsharing" }
    "fleet-service"   = { namespace = "carsharing" }
    "archive-service" = { namespace = "carsharing" }
    "kafka-client"    = { namespace = "carsharing" }
  }

  ci_service_accounts = {
    "kaniko-builder"       = { namespace = "ci" }
    "argocd-image-updater" = { namespace = "argocd" }
  }
}

resource "kubernetes_service_account_v1" "apps" {
  for_each = local.app_service_accounts

  metadata {
    name      = each.key
    namespace = each.value.namespace
    labels = {
      "app.kubernetes.io/name"         = each.key
      "app.kubernetes.io/part-of"      = "carsharing"
      "platform.carsharing/managed-by" = "terraform"
    }
  }

  automount_service_account_token = true
  depends_on                      = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_service_account_v1" "ci" {
  for_each = local.ci_service_accounts

  metadata {
    name      = each.key
    namespace = each.value.namespace
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_role_v1" "kaniko_builder" {
  metadata {
    name      = "kaniko-builder"
    namespace = "ci"
  }

  rule {
    api_groups = [""]
    resources  = ["secrets", "configmaps"]
    verbs      = ["get", "list"]
  }
  rule {
    api_groups = ["batch"]
    resources  = ["jobs"]
    verbs      = ["create", "get", "list", "watch", "delete"]
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_role_binding_v1" "kaniko_builder" {
  metadata {
    name      = "kaniko-builder"
    namespace = "ci"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.kaniko_builder.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = "kaniko-builder"
    namespace = "ci"
  }
  depends_on = [kubernetes_service_account_v1.ci]
}
