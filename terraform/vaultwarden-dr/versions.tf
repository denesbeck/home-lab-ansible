terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket  = "home-lab-terraform-state-a475fcee8baecef3"
    key     = "vaultwarden-dr/terraform.tfstate"
    region  = "eu-central-1"
    profile = "admin"
  }
}
