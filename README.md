# AWS Auto-Scale Optimizer

A Python/Boto3 infrastructure-as-code tool that deploys, dynamically scales, and cleanly destroys a secure AWS web architecture using EventBridge and Lambda.

This project goes beyond standard infrastructure deployment by integrating an event-driven automation layer. It deploys a highly available, load-balanced web tier and uses EventBridge to trigger a Lambda function that intelligently scales the Auto Scaling Group (ASG) up or down based on predefined shift schedules (e.g., morning traffic spikes, evening scale-downs). It includes a robust safety net, routing failed scaling events to an SQS queue and alerting administrators via SNS.

## Architecture Highlights

* **Network Layer:** Multi-AZ VPC, Internet Gateway, Public/Private Subnets, and Highly Available NAT Gateways.
* **Compute Layer:** Application Load Balancer (ALB), Target Groups, Launch Templates, and Auto Scaling Group (ASG) deployed across private subnets for enhanced security.
* **Automation Layer:** EventBridge (Cron schedules), AWS Lambda (scaling logic), SNS (Alerting), and SQS (Dead-letter/Retry Queue).

## Key Features

* **Idempotency:** Deployment scripts check for existing resources before creation, ensuring safe, repeatable executions.
* **Declarative YAML Configuration:** Abstracted configuration (`config.yaml`) allows easy adjustments to VPC CIDRs, instance types, and Cron schedules without altering the core Python codebase.
* **Automated Teardown:** A complete teardown script (`main_destroy.py`) that cleanly handles complex dependency resolution (e.g., draining ALBs, detaching IGWs) to prevent lingering AWS charges.
* **Graceful Failure Handling:** If the Lambda function fails to scale the ASG, it pushes the payload to an SQS queue and fires an SNS notification.

## Project Structure

```text
aws-autoscale-optimizer/
├── config.yaml               # Central configuration file
├── main_deploy.py            # Master script to provision all layers
├── main_destroy.py           # Master script to cleanly destroy all layers
├── network/
│   ├── CreateNetwork.py      # Provisions VPC, Subnets, IGW, NATs, Routes
│   └── TearDownNetwork.py
├── compute/
│   ├── CreateCompute.py      # Provisions ALB, ASG, Launch Templates, SGs
│   └── TearDownCompute.py
├── automation/
│   ├── CreateLambdaEvent.py  # Provisions EventBridge, Lambda, IAM Roles
│   ├── scale_asg.py          # Lambda function logic
│   └── TearDownLambdaEvent.py
└── utils/
    └── config_loader.py      # YAML parser and standard logging setup
