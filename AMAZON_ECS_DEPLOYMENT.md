# Purple AI MCP - Deployment on Amazon Elastic Container Service (ECS)

This guide will take you through deploying the Purple AI MCP Server to Amazon Elastic Container Service (ECS) 

> **NOTE:** A SentinelOne account is required to obtain the console token needed for authentication.

## Prerequisites

**Obtain a Sentinelone Singularity Operations Center console token**

This can be found in Policy & Settings → User Management → Service Users in your console. Currently, this server only supports tokens that have access to a single Account or Site. If you need to access multiple sites, you will need to run multiple MCP servers with Account-specific or Site-specific tokens.

**Prepare Environment Variables** 

```bash
PURPLEMCP_CONSOLE_BASE_URL=https://your-console.sentinelone.net
PURPLEMCP_CONSOLE_TOKEN=your-token
MCP_MODE=streamable-http 
PURPLEMCP_STATELESS_HTTP=True
```

**Prepare AWS Environment**

### VPC Configuration

 **Outbound internet access** - Outbound internet access should be permitted through an Internet Gateway or NAT Gateway. \
 **Security Groups** - 
 - Allow inbound HTTPS on port 443 (Towards ALB)
 - Allow outbound HTTPS on port 443 to connect to the Sentinelone service. 
 

It is important to note that Purple AI MCP does not include built-in authentication. For network exposed AWS deployments, ensure the MCP Server is placed behind an Application Load Balancer (ALB) with the appropriate timeout settings. Detailed information on production setups can be found [here](PRODUCTION_SETUP.md#cloud-load-balancer-setup).

### Secrets Manager

For secure usage of the `PURPLEMCP_CONSOLE_BASE_URL` and `PURPLEMCP_CONSOLE_TOKEN` best practice dictates storing them in AWS Secrets Manager with their respective KEY/VALUE pairs. You can then reference the secret when creating the task definition below.

### IAM Configuration
Deploying Purple AI MCP Server to ECS will require the creation of a new IAM role.

Trust Policy
```json
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```
IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:CreateLogGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:your-secret-name*" 
    }
  ]
}
```

## ECS Deployment Instructions : Quick Start

This example assumes that you will be deploying to ECS Fargate (Serverless). However, Purple AI MCP can also be deployed to Managed & Self Managed instances. It's also important to note that this setup will need tweaking based on your specific environment needs. i.e. ALB, Security Groups, VPC / Subnet configuration.

1. Create a new ECS cluster 
```bash
aws ecs create-cluster \
--cluster-name <CLUSTERNAME> \
--region <REGION>
```

2. Create a new task definition (the example below can be used for reference)
```json
{
  "family": "purple-mcp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "runtimePlatform": {
    "cpuArchitecture": "ARM64",
    "operatingSystemFamily": "LINUX"
  },
  "executionRoleArn": "arn:aws:iam::{{accountId}}:role/your-role",
  "containerDefinitions": [
    {
      "name": "purple-mcp",
      "image": "709825985650.dkr.ecr.us-east-1.amazonaws.com/sentinelone/purple-ai-mcp-server:latest",
      "cpu": 512,
      "memory": 1024,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MCP_MODE",
          "value": "streamable-http"
        },
        {
          "name": "PURPLEMCP_STATELESS_HTTP",
          "value": "True"
        }
      ],
      "secrets": [
        {
          "name": "PURPLEMCP_CONSOLE_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:{{region}}:{{accountId}}:secret:your-secret-name:PURPLEMCP_CONSOLE_TOKEN::"
        },
        {
          "name": "PURPLEMCP_CONSOLE_BASE_URL",
          "valueFrom": "arn:aws:secretsmanager:{{region}}:{{accountId}}:secret:your-secret-name:PURPLEMCP_CONSOLE_BASE_URL::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/purple-mcp",
          "awslogs-region": "{{region}}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
```
3. Create a new service within the ECS cluster
```bash
aws ecs create-service \
  --cluster purple-mcp-cluster \
  --service-name purple-mcp-service \
  --task-definition purple-mcp \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnets>],securityGroups=[<security groups>],assignPublicIp=ENABLED}" \
  --region <region>
  ```

Test the Purple AI MCP Server ECS deployment from an MCP compatible client. More information on the tools available can be found [here](README.md#available-tools)

## Useful Links

[Production VPC Setup for Purple AI MCP](PRODUCTION_SETUP.md) \
[Amazon Elastic Container Service Overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html) \
[Granting a VPC Internet Access via Internet Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html) \
[Creating custom IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html)