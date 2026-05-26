variable "kubeconfig" {
  description = "Путь к kubeconfig"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Имя kube-контекста (имя minikube-профиля)"
  type        = string
  default     = "carsharing"
}

variable "namespaces" {
  description = "Список неймспейсов платформы и их ярлыки"
  type = map(object({
    istio_injection = bool
    labels          = map(string)
  }))
  default = {
    "carsharing" = {
      istio_injection = true
      labels = {
        "app.kubernetes.io/part-of" = "carsharing"
        "tier"                      = "application"
      }
    }
    "data" = {
      istio_injection = false
      labels = {
        "tier" = "data"
      }
    }
    "ingress" = {
      istio_injection = false
      labels = {
        "tier" = "edge"
      }
    }
    "observability" = {
      istio_injection = false
      labels = {
        "tier" = "observability"
      }
    }
    "argocd" = {
      istio_injection = false
      labels = {
        "tier" = "platform"
      }
    }
    "ci" = {
      istio_injection = false
      labels = {
        "tier" = "platform"
      }
    }
    "ratelimit" = {
      istio_injection = true
      labels = {
        "tier" = "edge"
      }
    }
  }
}

variable "image_registry" {
  description = "Внутренний registry для образов микросервисов"
  type        = string
  default     = "registry.ci.svc.cluster.local:5000"
}

variable "image_registry_username" {
  description = "Пользователь внутреннего registry"
  type        = string
  default     = "carsharing"
}

variable "image_registry_password" {
  description = "Пароль внутреннего registry"
  type        = string
  sensitive   = true
  default     = "carsharing"
}
