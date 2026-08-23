#
#
# Designing a classical Web Application infrastructure
#
#
#


    #             INTERNET
    #                 │
    #                 ▼
    #          Internet Gateway
    #                 │
    #                 ▼
    #         Public Subnet
    #                 │
    #                 ▼
    #                ALB
    #                 │
    #       ┌─────────┴─────────┐
    #       ▼                   ▼
    #  Private Subnet       Private Subnet
    #       │                   │
    #      EC2                 EC2


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



# Create a new AWS VPC with CIDR 10.0.0.0/16
resource "aws_vpc" "vpc_0001" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "test-vpc-0001"
  }
}



locals {
  subnets = {
    "0001" = { cidr = "10.0.1.0/24", az = "eu-central-1a", type = "private" }
    "0002" = { cidr = "10.0.2.0/24", az = "eu-central-1b", type = "private" }
    "0003" = { cidr = "10.0.3.0/24", az = "eu-central-1a", type = "public"  }
    "0004" = { cidr = "10.0.4.0/24", az = "eu-central-1b", type = "public"  }
  }
}

resource "aws_subnet" "snet" {
  for_each = local.subnets

  vpc_id            = aws_vpc.vpc_0001.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = {
    Name = "test-snet-${each.key}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.vpc_0001.id

  tags = {
    Name = "test-igw-0001"
  }
}

# Generate a route table not containing the Internet Gateway
# as default route for 0.0.0.0/0 -> this makes any service
# within the subnet not directly accessible from the internet
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.vpc_0001.id

  tags = {
    Name = "test-table-private-0001"
  }
}

# Generate a route table containing the Internet Gateway
# as default route for 0.0.0.0/0 -> this makes any service
# within the subnet potentially accessible from the internet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc_0001.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "test-table-public-0001"
  }
}

# Associate the route tables to the subnets
resource "aws_route_table_association" "rt_association" {
  for_each = local.subnets

  subnet_id      = aws_subnet.snet[each.key].id
  route_table_id = each.value.type == "public" ? aws_route_table.public.id : aws_route_table.private.id
}


resource "aws_security_group" "alb" {
    name        = "test-alb-sg-0001"
    description = "BOH"
    vpc_id      = aws_vpc.vpc_0001.id


    # Since a Security Group is stateful, allowing inbound traffic
    # on a port automatically allows the corresponding response
    # traffic out. We only need egress open so the ALB can forward
    # requests onward to the EC2 targets.

    ingress {
        description = "Allow HTTP traffic inbound"
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        description = "Allow all outbound traffic"
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "test-alb-sg-0001"
    }
}


# Create an Application Load Balancer using as subnets any instance which is
# public
resource "aws_lb" "balancer" {
  name               = "test-alb-0001"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]

  subnets = [
    for key, subnet in local.subnets : aws_subnet.snet[key].id
    if subnet.type == "public"
  ]
}


# Define the Load Balancer Target Group: this defines the set of resources
# the ALB will forward requests to
resource "aws_lb_target_group" "main" {
  name     = "test-tg-0001"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.vpc_0001.id

  health_check {
    path                = "/"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
    timeout             = 5
  }

  tags = {
    Name = "test-tg-0001"
  }
}

# Define the Load Balancer Listener: this defines the set of resources the ALB
# is expected to 
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.balancer.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}


# Generate the two EC2 instances
data "aws_ssm_parameter" "linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_security_group" "ec2" {
    name        = "test-ec2-sg-0001"
    description = "BOH"
    vpc_id      = aws_vpc.vpc_0001.id

    # Instead of setting the cidr blocks which is allowed to open
    # to the EC2 instances, we use the Security Group of the ALB,
    # which means the EC2 is authorized to accept traffic coming
    # ANY resource using as security group that the ALB is using.
    ingress {
        description     = "HTTP from ALB"
        from_port       = 80
        to_port         = 80
        protocol        = "tcp"
        security_groups = [aws_security_group.alb.id]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "test-ec2-sg-0001"
    }
}

locals {
    instances = {
        "0001" = { subnet_key = "0001" }
        "0002" = { subnet_key = "0002" }
    }
}

resource "aws_instance" "linux" {
    for_each = local.instances

    ami                         = data.aws_ssm_parameter.linux.value
    instance_type               = "t3.micro"
    subnet_id                   = aws_subnet.snet[each.value.subnet_key].id
    associate_public_ip_address = false

    vpc_security_group_ids = [aws_security_group.ec2.id]

    tags = {
        Name = "replica-${each.key}"
    }
}

# Register the EC2 instances as targets of the ALB
resource "aws_lb_target_group_attachment" "app" {
  for_each = aws_instance.linux

  target_group_arn = aws_lb_target_group.main.arn
  target_id        = each.value.id
  port              = 80
}


# DNS name to reach the application through the ALB
output "alb_dns_name" {
  value = aws_lb.balancer.dns_name
}
