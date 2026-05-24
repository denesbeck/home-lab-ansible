terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Uncomment after bootstrapping the state bucket (see README)
  backend "s3" {
    bucket  = "home-lab-terraform-state-a475fcee8baecef3"
    key     = "home-lab/terraform.tfstate"
    region  = "eu-central-1"
    profile = "admin"
  }
}
