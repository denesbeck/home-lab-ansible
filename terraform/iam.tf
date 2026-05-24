resource "aws_iam_user" "vaultwarden_backup" {
  name = "vaultwarden-backup"
}

resource "aws_iam_user_policy" "vaultwarden_backup" {
  name = "VaultwardenS3PutObjectPolicy"
  user = aws_iam_user.vaultwarden_backup.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.vaultwarden_backup.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_access_key" "vaultwarden_backup" {
  user = aws_iam_user.vaultwarden_backup.name
}
