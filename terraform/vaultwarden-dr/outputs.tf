output "cloudwatch_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.vaultwarden_heartbeat.arn
}

output "cloudwatch_recovery_alarm_arn" {
  value = aws_cloudwatch_metric_alarm.vaultwarden_heartbeat_recovery.arn
}

output "sns_alarm_topic_arn" {
  value = aws_sns_topic.vaultwarden_alarm.arn
}

output "sns_notifications_topic_arn" {
  value = aws_sns_topic.vaultwarden_notifications.arn
}

output "lambda_function_arn" {
  value = aws_lambda_function.failover.arn
}

output "launch_template_id" {
  value = aws_launch_template.failover.id
}
