resource "random_password" "postgres" {
  length  = 24
  special = false
}

resource "random_password" "redis" {
  length  = 24
  special = false
}

resource "random_password" "minio" {
  length  = 24
  special = false
}

resource "kubernetes_secret_v1" "postgres" {
  metadata {
    name      = "postgres-credentials"
    namespace = "data"
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  type = "Opaque"
  data = {
    POSTGRES_USER     = "carsharing"
    POSTGRES_PASSWORD = random_password.postgres.result
    POSTGRES_DB       = "carsharing"
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_secret_v1" "redis" {
  metadata {
    name      = "redis-credentials"
    namespace = "data"
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  type = "Opaque"
  data = {
    REDIS_PASSWORD = random_password.redis.result
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_secret_v1" "minio" {
  metadata {
    name      = "minio-credentials"
    namespace = "data"
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  type = "Opaque"
  data = {
    MINIO_ROOT_USER     = "carsharing"
    MINIO_ROOT_PASSWORD = random_password.minio.result
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_secret_v1" "image_pull" {
  for_each = toset(["carsharing", "ci"])

  metadata {
    name      = "registry-pull"
    namespace = each.key
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  type = "kubernetes.io/dockerconfigjson"
  data = {
    ".dockerconfigjson" = jsonencode({
      auths = {
        "${var.image_registry}" = {
          username = var.image_registry_username
          password = var.image_registry_password
          auth     = base64encode("${var.image_registry_username}:${var.image_registry_password}")
        }
      }
    })
  }
  depends_on = [kubernetes_namespace_v1.platform]
}

resource "kubernetes_config_map_v1" "app_endpoints" {
  metadata {
    name      = "app-endpoints"
    namespace = "carsharing"
    labels = {
      "platform.carsharing/managed-by" = "terraform"
    }
  }
  data = {
    POSTGRES_HOST   = "postgres.data.svc.cluster.local"
    MONGO_URI       = "mongodb://mongodb.data.svc.cluster.local:27017"
    REDIS_HOST      = "valkey.data.svc.cluster.local"
    CASSANDRA_HOST  = "cassandra.data.svc.cluster.local"
    KAFKA_BOOTSTRAP = "carsharing-kafka-bootstrap.data.svc.cluster.local:9092"
    S3_ENDPOINT     = "http://minio.data.svc.cluster.local:9000"
    OTEL_ENDPOINT   = "http://otel-collector.observability.svc.cluster.local:4317"
  }
  depends_on = [kubernetes_namespace_v1.platform]
}
