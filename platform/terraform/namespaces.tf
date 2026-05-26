resource "kubernetes_namespace_v1" "platform" {
  for_each = var.namespaces

  metadata {
    name = each.key

    labels = merge(
      each.value.labels,
      {
        "platform.carsharing/managed-by" = "terraform"
      },
      each.value.istio_injection ? { "istio-injection" = "enabled" } : {}
    )
  }
}
