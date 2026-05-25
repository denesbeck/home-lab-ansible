resource "aws_sns_topic" "vaultwarden_alarm" {
  name = "vaultwarden-alarm"
}

resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.vaultwarden_alarm.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.failover.arn
}

resource "aws_sns_topic" "vaultwarden_notifications" {
  name = "vaultwarden-notifications"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.vaultwarden_notifications.arn
  protocol  = "email"
  endpoint  = var.sns_email
}
