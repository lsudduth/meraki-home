variable "meraki_api_key" {
  description = "Meraki Dashboard API Key"
  type        = string
  sensitive   = true
  default     = ""

  validation {
    condition     = var.meraki_api_key != ""
    error_message = "meraki_api_key must be set (via environment variable TF_VAR_meraki_api_key or -var flag)"
  }
}
