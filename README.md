AWS Auto-Scale Optimizer
A Python/Boto3 infrastructure-as-code tool that deploys, dynamically scales, and cleanly destroys a secure AWS web architecture using EventBridge and Lambda.

This project goes beyond standard infrastructure deployment by integrating an event-driven automation layer. It deploys a highly available, load-balanced web tier and uses EventBridge to trigger a Lambda function that intelligently scales the Auto Scaling Group (ASG) up or down based on predefined shift schedules (e.g., morning traffic spikes, evening scale-downs). It includes a robust safety net, routing failed scaling events to an SQS queue and alerting administrators via SNS.

Architecture Highlights
Network Layer: Multi-AZ VPC, Internet Gateway, Public/Private Subnets, and Highly Available NAT Gateways.

Compute Layer: Application Load Balancer (ALB), Target Groups, Launch Templates, and Auto Scaling Group (ASG) deployed across private subnets for enhanced security.

Automation Layer: EventBridge (Cron schedules), AWS Lambda (scaling logic), SNS (Alerting), and SQS (Dead-letter/Retry Queue).

Key Features
Chaos Engineering & Fault Tolerance: Includes a built-in "chaos test" feature to intentionally trigger IAM Access Denied errors, proving the effectiveness of the error-handling routing. If the Lambda function fails to scale the ASG, it gracefully catches the error, pushes the failed payload to an SQS queue, and fires an SNS email notification to administrators.

Idempotency: Deployment scripts check for existing resources before creation, ensuring safe, repeatable executions.

YAML Configuration: Abstracted configuration (config.yaml) allows easy adjustments to VPC CIDRs, instance types, and Cron schedules without altering the core Python codebase.

Automated Teardown: A complete teardown script (main_destroy.py) that cleanly handles complex dependency resolution (e.g., draining ALBs, detaching IGWs) to prevent lingering AWS charges.

Demonstration & Logs
Because this project is built for automation and resilience, the deployment and error-handling mechanisms are logged and tracked:

Deployment & Teardown Logs: Review the complete terminal execution logs in the repository: Deployment Logs | Teardown Logs.

Chaos Testing (SQS & SNS): Below is the result of the Lambda function intentionally failing to scale an unauthorized ASG due to strict IAM least-privilege policies. The failure is successfully caught and routed to the safety net:

1. SQS Dead-Letter Queue catches the failed payload
2. SNS Topic fires an email alert to the Administrator
Project Structure
Plaintext
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
Usage Instructions
1. Clone and Configure

Bash
git clone https://github.com/gandhisiripuram/aws-autoscale-optimizer.git
cd aws-autoscale-optimizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Note: Edit config.yaml to set your desired region, CIDR blocks, and cron schedules before deploying.

2. Deploy Infrastructure

Bash
python main_deploy.py
Wait for the script to finish. The generated ALB DNS name will be printed in your terminal output (you can also reference the sample deployment_logs.txt.txt for expected output). Navigate to this URL in your browser to view the deployed application.

3. Destroy Infrastructure

Bash
python main_destroy.py
Skills Demonstrated
Infrastructure as Code (IaC): Engineered a highly available 3-tier AWS architecture using Python and Boto3 instead of declarative tools, demonstrating deep programmatic control over AWS APIs.

Event-Driven Automation: Designed a serverless scheduling mechanism using EventBridge and Lambda to dynamically optimize EC2 scaling based on traffic patterns, reducing idle compute costs.

Resilience & Chaos Engineering: Implemented strict IAM least-privilege policies and built a custom fault-tolerance pipeline that routes failed Lambda executions to an SQS dead-letter queue and triggers SNS admin alerts.

Idempotent CI/CD Practices: Developed modular deployment and teardown scripts with advanced state-checking and dependency resolution (e.g., automated ALB draining and ENI sweeping) to ensure safe, repeatable infrastructure management.
