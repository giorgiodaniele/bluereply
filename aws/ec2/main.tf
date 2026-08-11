terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-north-1"
}

# Define the latest Amazon Linux AMI
data "aws_ssm_parameter" "linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_region" "current" {}

data "aws_ec2_managed_prefix_list" "ec2_instance_connect" {
  name = "com.amazonaws.${data.aws_region.current.region}.ec2-instance-connect"
}


#
# GENERATE A BRAND NEW AWS VPC
#
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name          = "lab-vpc"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

#
# GENERATE SUBNETS WHERE AWS EC2 are going to be spawned
#
resource "aws_subnet" "snet_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = "eu-north-1a"

  tags = {
    Name          = "lab-public-subnet-a"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

resource "aws_subnet" "snet_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "eu-north-1b"

  tags = {
    Name          = "lab-public-subnet-b"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

resource "aws_subnet" "snet_c" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "eu-north-1c"

  tags = {
    Name          = "lab-public-subnet-c"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}


#
# GENERATE A BRAND NEW INTERNET GATEWAY - THIS ALLOWS TRAFFIC
# FROM THE INTERNET TO THE VPC AND VICE VERSA
#

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name          = "lab-igw"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

#
# DEFINE THE ROUTE TABLE THE VPC IS GOING TO USE
#

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name          = "lab-public-route-table"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

#
# ASSOCIATE THE ROUTE TABLE TO THE SUBNET (LIKE THEY WERE LANs)
#

resource "aws_route_table_association" "snet_a" {
  subnet_id      = aws_subnet.snet_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "snet_b" {
  subnet_id      = aws_subnet.snet_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "snet_c" {
  subnet_id      = aws_subnet.snet_c.id
  route_table_id = aws_route_table.public.id
}

# CREATE A NEW SECURITY GROUP
# THIS SECURITY GROUP CONTROLS INBOUND AND OUTBOUND TRAFFIC
# FOR THE ASSOCIATED NETWORK INTERFACES

resource "aws_security_group" "ssh" {
  name        = "lab-ssh-sg"
  description = "Allow SSH access to Linux EC2 instances"
  vpc_id      = aws_vpc.main.id

    #
    # CREATE INGRESS RULE
    # ALLOW INBOUND TCP TRAFFIC ON PORT 22 (SSH)
    # FROM THE AWS-MANAGED EC2 INSTANCE CONNECT PREFIX LIST
    #

  ingress {
    description     = "SSH from EC2 Instance Connect"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    prefix_list_ids = [
      data.aws_ec2_managed_prefix_list.ec2_instance_connect.id
    ]
  }
  
    #
    # CREATE EGRESS RULE
    # ALLOW ALL OUTBOUND TRAFFIC TO THE INTERNET
    #

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name          = "lab-ssh-sg"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

# A SECURITY GROUP IS A STATEFUL FIREWALL WORKING AT THE
# RESOURCE / ENI LEVEL.
#
# A NACL (NETWORK ACCESS CONTROL LIST) IS A STATELESS FIREWALL
# WORKING AT THE SUBNET LEVEL.

#
# GENERATE EVENTUALLY THE EC2 INSTANCES
#

resource "aws_instance" "linux_a" {
  ami           = data.aws_ssm_parameter.linux.value
  instance_type = "t3.micro"

  subnet_id = aws_subnet.snet_a.id

  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.ssh.id
  ]

  tags = {
    Name          = "linux-a"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

resource "aws_instance" "linux_b" {
  ami           = data.aws_ssm_parameter.linux.value
  instance_type = "t3.micro"

  subnet_id = aws_subnet.snet_b.id

  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.ssh.id
  ]

  tags = {
    Name          = "linux-b"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}

resource "aws_instance" "linux_c" {
  ami           = data.aws_ssm_parameter.linux.value
  instance_type = "t3.micro"

  subnet_id = aws_subnet.snet_c.id

  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.ssh.id
  ]

  tags = {
    Name          = "linux-c"
    Environment   = "dev"
    Application   = "lab"
    Owner         = "g.luppina@reply.it"
    Business_Unit = "BLUTIT_IT"
  }
}