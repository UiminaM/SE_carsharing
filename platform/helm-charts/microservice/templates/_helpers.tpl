{{- define "ms.name" -}}
{{- default .Chart.Name .Values.name -}}
{{- end -}}

{{- define "ms.fullName" -}}
{{- default (include "ms.name" .) .Values.fullName -}}
{{- end -}}

{{- define "ms.labels" -}}
app.kubernetes.io/name: {{ include "ms.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: "{{ .Chart.AppVersion }}"
app.kubernetes.io/part-of: carsharing
app.kubernetes.io/managed-by: helm
{{- end -}}

{{- define "ms.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ms.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ms.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "ms.fullName" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default (include "ms.fullName" .) .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
