resource "random_id" "state_bucket_suffix" {
  byte_length = 8
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "home-lab-terraform-state-${random_id.state_bucket_suffix.hex}"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "vaultwarden_backup" {
  bucket = "vaultwarden-backup-${random_id.state_bucket_suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "vaultwarden_backup" {
  bucket = aws_s3_bucket.vaultwarden_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "vaultwarden_backup" {
  bucket = aws_s3_bucket.vaultwarden_backup.id

  rule {
    id     = "expire-old-backups"
    status = "Enabled"

    filter {}

    expiration {
      days = 3
    }
  }
}
