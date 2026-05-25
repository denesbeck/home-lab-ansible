resource "aws_cloudwatch_metric_alarm" "vaultwarden_heartbeat" {
  alarm_name          = "vaultwarden-heartbeat"
  alarm_description   = "Triggers failover when heartbeat missing for 3 minutes, teardown when it returns"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Heartbeat"
  namespace           = "Vaultwarden"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.vaultwarden_alarm.arn]
  ok_actions    = [aws_sns_topic.vaultwarden_alarm.arn]
}
