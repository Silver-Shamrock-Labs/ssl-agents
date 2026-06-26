locals {
  lambda_zip = "${path.module}/../dist/lambda.zip"
}

resource "aws_iam_role" "lambda" {
  name = "ssl-agents-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "slack" {
  function_name    = "ssl-agents-slack"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  handler          = "slack.app.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda.arn
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      SLACK_BOT_TOKEN           = var.slack_bot_token
      SLACK_SIGNING_SECRET      = var.slack_signing_secret
      CODING_ROUTINE_TRIGGER_ID = var.coding_routine_trigger_id
      CODING_ROUTINE_TOKEN      = var.coding_routine_token
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ssl-agents"
  }
}

resource "aws_apigatewayv2_api" "slack" {
  name          = "ssl-agents"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.slack.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.slack.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "slack_events" {
  api_id    = aws_apigatewayv2_api.slack.id
  route_key = "POST /slack/events"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.slack.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack.execution_arn}/*/*"
}

output "slack_events_url" {
  description = "Set this as the Slack Event Subscriptions Request URL"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/slack/events"
}
