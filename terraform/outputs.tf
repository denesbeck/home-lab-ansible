output "terraform_state_bucket" {
  value = aws_s3_bucket.terraform_state.id
}

output "vaultwarden_backup_bucket" {
  value = aws_s3_bucket.vaultwarden_backup.id
}

output "vaultwarden_backup_access_key_id" {
  value = aws_iam_access_key.vaultwarden_backup.id
}

output "vaultwarden_backup_secret_access_key" {
  value     = aws_iam_access_key.vaultwarden_backup.secret
  sensitive = true
}
