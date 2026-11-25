# Northwind Bank — Payments Platform (AWS, eu-west-1). Fictional sample estate.

resource "aws_vpc" "main" {
  tags = {
    criticality = "tier1"
    monthly_usd = "800"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id = aws_vpc.main.id
  tags = {
    criticality = "tier1"
    monthly_usd = "50"
  }
}

resource "aws_security_group" "payments" {
  vpc_id = aws_vpc.main.id
  tags = {
    criticality = "tier1"
    monthly_usd = "0"
  }
}

resource "aws_lb" "public" {
  security_groups = [aws_security_group.payments.id]
  tags = {
    criticality = "tier1"
    monthly_usd = "1200"
  }
}

resource "aws_kms_key" "data" {
  tags = {
    criticality = "tier1"
    monthly_usd = "300"
  }
}

resource "aws_iam_role" "payments" {
  tags = {
    criticality = "tier1"
    monthly_usd = "0"
  }
}

resource "aws_iam_role" "lambda_exec" {
  tags = {
    criticality = "tier2"
    monthly_usd = "0"
  }
}

resource "aws_iam_policy" "payments_access" {
  tags = {
    criticality = "tier1"
    monthly_usd = "0"
  }
}

resource "aws_cognito_user_pool" "customers" {
  tags = {
    criticality = "tier1"
    monthly_usd = "2500"
  }
}

resource "aws_secretsmanager_secret" "db_creds" {
  kms_key_id = aws_kms_key.data.arn
  tags = {
    criticality = "tier1"
    monthly_usd = "100"
  }
}

resource "aws_eks_cluster" "payments" {
  role_arn = aws_iam_role.payments.arn
  tags = {
    criticality = "tier1"
    monthly_usd = "18000"
  }
}

resource "aws_instance" "legacy_batch" {
  tags = {
    criticality = "tier3"
    monthly_usd = "2200"
  }
}

resource "aws_lambda_function" "fraud_score" {
  role = aws_iam_role.lambda_exec.arn
  tags = {
    criticality = "tier1"
    monthly_usd = "4000"
  }
}

resource "aws_lambda_function" "notify" {
  role = aws_iam_role.lambda_exec.arn
  tags = {
    criticality = "tier2"
    monthly_usd = "600"
  }
}

resource "aws_lambda_function" "reconcile" {
  role = aws_iam_role.lambda_exec.arn
  tags = {
    criticality = "tier1"
    monthly_usd = "1800"
  }
}

resource "aws_api_gateway_rest_api" "public" {
  # fronts aws_lambda_function.fraud_score
  uri = aws_lambda_function.fraud_score.invoke_arn
  tags = {
    criticality = "tier1"
    monthly_usd = "1500"
  }
}

resource "aws_sfn_state_machine" "settlement" {
  role_arn = aws_iam_role.lambda_exec.arn
  definition = aws_lambda_function.reconcile.arn
  tags = {
    criticality = "tier1"
    monthly_usd = "900"
  }
}

resource "aws_dynamodb_table" "ledger" {
  kms_key_arn = aws_kms_key.data.arn
  tags = {
    criticality = "tier1"
    data_gb     = "40000"
    monthly_usd = "22000"
  }
}

resource "aws_dynamodb_table" "sessions" {
  tags = {
    criticality = "tier2"
    data_gb     = "200"
    monthly_usd = "1800"
  }
}

resource "aws_rds_cluster" "core_banking" {
  kms_key_id = aws_kms_key.data.arn
  tags = {
    criticality = "tier1"
    data_gb     = "12000"
    monthly_usd = "15000"
  }
}

resource "aws_redshift_cluster" "risk_dw" {
  tags = {
    criticality = "tier2"
    data_gb     = "150000"
    monthly_usd = "30000"
  }
}

resource "aws_s3_bucket" "documents" {
  # kms: aws_kms_key.data
  kms = aws_kms_key.data.arn
  tags = {
    criticality = "tier1"
    data_gb     = "250000"
    monthly_usd = "6000"
  }
}

resource "aws_s3_bucket" "audit_logs" {
  tags = {
    criticality = "tier1"
    data_gb     = "90000"
    monthly_usd = "2000"
  }
}

resource "aws_kinesis_stream" "transactions" {
  tags = {
    criticality = "tier1"
    data_gb     = "5000"
    monthly_usd = "5000"
  }
}

resource "aws_sqs_queue" "payment_events" {
  tags = {
    criticality = "tier1"
    monthly_usd = "400"
  }
}

resource "aws_sns_topic" "alerts" {
  tags = {
    criticality = "tier2"
    monthly_usd = "100"
  }
}

resource "aws_sagemaker_endpoint" "fraud_model" {
  role = aws_iam_role.payments.arn
  tags = {
    criticality = "tier1"
    data_gb     = "50"
    monthly_usd = "12000"
  }
}

resource "aws_glue_job" "etl_risk" {
  target = aws_redshift_cluster.risk_dw.id
  tags = {
    criticality = "tier2"
    monthly_usd = "3500"
  }
}

resource "aws_cloudfront_distribution" "web" {
  tags = {
    criticality = "tier1"
    monthly_usd = "1800"
  }
}

resource "aws_route53_zone" "bank" {
  tags = {
    criticality = "tier1"
    monthly_usd = "50"
  }
}

resource "aws_cloudwatch_log_group" "platform" {
  tags = {
    criticality = "tier2"
    monthly_usd = "2500"
  }
}

resource "aws_cloudwatch_metric_alarm" "latency" {
  tags = {
    criticality = "tier2"
    monthly_usd = "20"
  }
}

