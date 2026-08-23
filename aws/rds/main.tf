terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

#
# GENERATE A NEW VIRTUAL PRIVATE CLOUD
#

resource "aws_vpc" "vpc_0001" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "test-vpc-0001"
  }
}

#
# GENERATE A NEW INTERNET GATEWAY - THIS ALLOWS ANYTHING
# PROVISIONED IN THE VPC TO CONNECT TO THE INTERNET
#

resource "aws_internet_gateway" "igw_0001" {
  vpc_id = aws_vpc.vpc_0001.id

  tags = {
    Name = "test-igw-0001"
  }
}

#
# GENERATE SNET-001
#

resource "aws_subnet" "snet_0001" {
  vpc_id            = aws_vpc.vpc_0001.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = local.azs[0]

  tags = {
    Name = "test-snet-0001"
  }
}

#
# GENERATE SNET-002
#

resource "aws_subnet" "snet_0002" {
  vpc_id            = aws_vpc.vpc_0001.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = local.azs[1]

  tags = {
    Name = "test-snet-0002"
  }
}

#
# GENERATE SNET-002
#

resource "aws_subnet" "snet_0003" {
  vpc_id            = aws_vpc.vpc_0001.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = local.azs[2]

  tags = {
    Name = "test-snet-0003"
  }
}


#
# CREATE A NEW ROUTE TABLE WHICH CAN BE ASSOCIATED
# TO A SUBNET TO MAKE IT AS "PUBLIC", WHICH MEANS
# ANY SERVICE PROVISIONED IN THAT SUBNET CAN POTENTIALLY
# ACCESS THE INTERNET AND GETS ACCESED FROM INTERNET
#

resource "aws_route_table" "rt_public_0001" {
  vpc_id = aws_vpc.vpc_0001.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_0001.id
  }

  tags = {
    Name = "test-rt-0001"
  }
}

#
# ASSOCIATE
#

resource "aws_route_table_association" "snet_0001" {
  subnet_id      = aws_subnet.snet_0001.id
  route_table_id = aws_route_table.rt_public_0001.id        # IT BECOMES A PUBLIC SUBNET
}

resource "aws_route_table_association" "snet_0002" {
  subnet_id      = aws_subnet.snet_0002.id
  route_table_id = aws_route_table.rt_public_0001.id        # IT BECOMES A PUBLIC SUBNET
}

resource "aws_route_table_association" "snet_0003" {
  subnet_id      = aws_subnet.snet_0003.id
  route_table_id = aws_route_table.rt_public_0001.id        # IT BECOMES A PUBLIC SUBNET
}

#
# GENERATE A NEW SUBNET GROUP - THIS COLLECTS ALL SUBNETS WHERE REPLICAS
# CAN BE PROVISIONED WITHIN A VPC, IN A GIVEN REGION
#

resource "aws_db_subnet_group" "db_subnet_group_0001" {
  name = "db-subnet-group-0001"

  subnet_ids = [
    aws_subnet.snet_0001.id,
    aws_subnet.snet_0002.id,
    aws_subnet.snet_0003.id
  ]

  tags = {
    Name = "test-sg-0001"
  }
}

#
# GENERATE A NEW SECURITY GROUP - THIS IS LIKE THE NETWORK SECURITY GROUP
# THAT CAN BE ATTACHED TO THE ENI OF A EC2 INSTANCE
#

resource "aws_security_group" "rds_sg_0001" {
  name        = "test-sg-0001"
  description = "Security Group for PostgreSQL RDS"
  vpc_id      = aws_vpc.vpc_0001.id

  ingress {
    description = "PostgreSQL"
    protocol    = "tcp"
    from_port   = 5432
    to_port     = 5432
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound traffic"
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "test-sg-0001"
  }
}


#
# CREATE A NEW RDS INSTANCE
#

resource "aws_db_instance" "postgres_0001" {

  identifier           = "test-db"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_type         = "gp3"
  storage_encrypted    = true
  db_name              = "reply"
  username             = "postgres"
  password             = "C34B1bb22"
  port                 = 5432
  db_subnet_group_name = aws_db_subnet_group.db_subnet_group_0001.name

  vpc_security_group_ids = [
    aws_security_group.rds_sg_0001.id
  ]


  publicly_accessible        = true          # IT IS PUBLIC
  multi_az                   = false         # IT CAN BE SPAWNED IN A SINGLE AZ
  backup_retention_period    = 1
  deletion_protection        = false
  skip_final_snapshot        = true
  apply_immediately          = true
  auto_minor_version_upgrade = true

  tags = {
    Name = "test-db-0001"
  }
}


#
#
# OUTPUTS ALL INFOs to connect
#
#