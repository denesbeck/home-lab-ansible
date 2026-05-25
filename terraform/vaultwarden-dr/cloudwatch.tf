resource "aws_cloudwatch_metric_alarm" "vaultwarden_heartbeat" {
  alarm_name          = "vaultwarden-heartbeat-missing"
  alarm_description   = "Triggers when Vaultwarden heartbeat is missing for 3 minutes"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Heartbeat"
  namespace           = "Vaultwarden"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"

  alarm_actions = [aws_sns_topic.vaultwarden_alarm.arn]
}

resource "aws_cloudwatch_metric_alarm" "vaultwarden_heartbeat_recovery" {
  alarm_name          = "vaultwarden-heartbeat-recovered"
  alarm_description   = "Triggers automated teardown when heartbeat returns for 10 consecutive minutes"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 10
  metric_name         = "Heartbeat"
  namespace           = "Vaultwarden"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"

  ok_actions = [aws_sns_topic.vaultwarden_alarm.arn]
}
