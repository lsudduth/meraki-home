terraform {
  backend "s3" {
    bucket         = "meraki-home-terraform-state"
    key            = "meraki-home/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
