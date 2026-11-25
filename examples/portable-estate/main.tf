# Fabrikam Regional Government Portal (AWS, but built on open standards). Fictional.

resource "aws_vpc" "main" {
  tags = {
    criticality = "tier1"
    monthly_usd = "400"
  }
}

resource "aws_security_group" "app" {
  vpc_id = aws_vpc.main.id
  tags = {
    criticality = "tier1"
    monthly_usd = "0"
  }
}

resource "aws_eks_cluster" "portal" {
  tags = {
    criticality = "tier1"
    monthly_usd = "6000"
  }
}

resource "aws_instance" "bastion" {
  tags = {
    criticality = "tier3"
    monthly_usd = "150"
  }
}

resource "aws_db_instance" "citizens" {
  # engine = postgres
  engine = "postgres"
  tags = {
    criticality = "tier1"
    data_gb     = "4000"
    monthly_usd = "5000"
  }
}

resource "aws_elasticache_cluster" "cache" {
  tags = {
    criticality = "tier2"
    data_gb     = "20"
    monthly_usd = "600"
  }
}

resource "aws_msk_cluster" "events" {
  tags = {
    criticality = "tier1"
    data_gb     = "800"
    monthly_usd = "3000"
  }
}

resource "aws_s3_bucket" "records" {
  tags = {
    criticality = "tier1"
    data_gb     = "60000"
    monthly_usd = "1500"
  }
}

resource "aws_secretsmanager_secret" "app" {
  tags = {
    criticality = "tier1"
    monthly_usd = "50"
  }
}

resource "aws_route53_zone" "gov" {
  tags = {
    criticality = "tier1"
    monthly_usd = "50"
  }
}

