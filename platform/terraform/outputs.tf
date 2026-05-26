output "namespaces" {
  value       = [for ns in kubernetes_namespace_v1.platform : ns.metadata[0].name]
  description = "Список созданных неймспейсов"
}

output "service_accounts_carsharing" {
  value       = [for sa in kubernetes_service_account_v1.apps : sa.metadata[0].name]
  description = "Service accounts приложений"
}

output "service_accounts_ci" {
  value       = [for sa in kubernetes_service_account_v1.ci : "${sa.metadata[0].namespace}/${sa.metadata[0].name}"]
  description = "Service accounts платформенных CI-компонентов"
}

output "base_secrets" {
  value = {
    postgres   = "${kubernetes_secret_v1.postgres.metadata[0].namespace}/${kubernetes_secret_v1.postgres.metadata[0].name}"
    redis      = "${kubernetes_secret_v1.redis.metadata[0].namespace}/${kubernetes_secret_v1.redis.metadata[0].name}"
    minio      = "${kubernetes_secret_v1.minio.metadata[0].namespace}/${kubernetes_secret_v1.minio.metadata[0].name}"
    image_pull = [for secret in kubernetes_secret_v1.image_pull : "${secret.metadata[0].namespace}/${secret.metadata[0].name}"]
  }
  description = "Базовые секреты, созданные Terraform"
  sensitive   = true
}

output "app_endpoints_config_map" {
  value       = "${kubernetes_config_map_v1.app_endpoints.metadata[0].namespace}/${kubernetes_config_map_v1.app_endpoints.metadata[0].name}"
  description = "ConfigMap с базовыми endpoint-ами платформы"
}

output "image_registry" {
  value       = var.image_registry
  description = "Адрес внутреннего registry"
}
