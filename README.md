# AWS Auto-Scale Optimizer

A Python/Boto3 infrastructure-as-code tool that deploys, dynamically scales, and cleanly destroys a secure AWS web architecture using EventBridge and Lambda.

This project goes beyond standard infrastructure deployment by integrating an event-driven automation layer. It deploys a highly available, load-balanced web tier and uses EventBridge to trigger a Lambda function that intelligently scales the Auto Scaling Group (ASG) up or down based on predefined shift schedules (e.g., morning traffic spikes, evening scale-downs). It includes a robust safety net, routing failed scaling events to an SQS queue and alerting administrators via SNS.

## Architecture Highlights

  * **Network Layer:** Multi-AZ VPC, Internet Gateway, Public/Private Subnets, and Highly Available NAT Gateways.
  * **Compute Layer:** Application Load Balancer (ALB), Target Groups, Launch Templates, and Auto Scaling Group (ASG) deployed across private subnets for enhanced security.
  * **Automation Layer:** EventBridge (Cron schedules), AWS Lambda (scaling logic), SNS (Alerting), and SQS (Dead-letter/Retry Queue).

## Key Features

  * **Chaos Engineering & Fault Tolerance:** Includes a built-in "chaos test" feature to intentionally trigger IAM Access Denied errors, proving the effectiveness of the error-handling routing. If the Lambda function fails to scale the ASG, it gracefully catches the error, pushes the failed payload to an SQS queue, and fires an SNS email notification to administrators.
  * **Idempotency:** Deployment scripts check for existing resources before creation, ensuring safe, repeatable executions.
  * **YAML Configuration:** Abstracted configuration (config.yaml) allows easy adjustments to VPC CIDRs, instance types, and Cron schedules without altering the core Python codebase.
  * **Automated Teardown:** A complete teardown script (main\_destroy.py) that cleanly handles complex dependency resolution (e.g., draining ALBs, detaching IGWs) to prevent lingering AWS charges.

## Project Structure

aws-autoscale-optimizer/
├── config.yaml               \# Central configuration file
├── main\_deploy.py            \# Master script to provision all layers
├── main\_destroy.py           \# Master script to cleanly destroy all layers
├── network/
│   ├── CreateNetwork.py      \# Provisions VPC, Subnets, IGW, NATs, Routes
│   └── TearDownNetwork.py
├── compute/
│   ├── CreateCompute.py      \# Provisions ALB, ASG, Launch Templates, SGs
│   └── TearDownCompute.py
├── automation/
│   ├── CreateLambdaEvent.py  \# Provisions EventBridge, Lambda, IAM Roles
│   ├── scale\_asg.py          \# Lambda function logic
│   └── TearDownLambdaEvent.py
└── utils/
└── config\_loader.py      \# YAML parser and standard logging setup

## Usage Instructions

**1. Clone and Configure**
git clone [https://github.com/gandhisiripuram/aws-autoscale-optimizer.git](https://www.google.com/search?q=https://github.com/gandhisiripuram/aws-autoscale-optimizer.git)
cd aws-autoscale-optimizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

*Note: Edit config.yaml to set your desired region, CIDR blocks, and cron schedules before deploying.*

**2. Deploy Infrastructure**
python main\_deploy.py

*Wait for the script to output the ALB DNS name. You can navigate to this URL to view the deployed application.*

**3. Destroy Infrastructure**
python main\_destroy.py

## Skills Demonstrated (Resume Highlights)

  * **Infrastructure as Code (IaC):** Engineered a highly available 3-tier AWS architecture using Python and Boto3 instead of declarative tools, demonstrating deep programmatic control over AWS APIs.
  * **Event-Driven Automation:** Designed a serverless scheduling mechanism using EventBridge and Lambda to dynamically optimize EC2 scaling based on traffic patterns, reducing idle compute costs.
  * **Resilience & Chaos Engineering:** Implemented strict IAM least-privilege policies and built a custom fault-tolerance pipeline that routes failed Lambda executions to an SQS dead-letter queue and triggers SNS admin alerts.
  * **Idempotent CI/CD Practices:** Developed modular deployment and teardown scripts with advanced state-checking and dependency resolution (e.g., automated ALB draining and ENI sweeping) to ensure safe, repeatable infrastructure management.
