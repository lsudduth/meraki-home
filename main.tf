terraform {
  required_providers {
    meraki = {
      source  = "ciscodevnet/meraki"
      version = "~> 1.8"
    }
  }
}

provider "meraki" {
  api_key = var.meraki_api_key
}

module "meraki" {
  source  = "netascode/nac-meraki/meraki"
  version = "0.6.0"

  yaml_directories          = ["data/"]
  write_default_values_file = "defaults.yaml"
}
