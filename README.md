# AWS Auto-Scale Optimizer

![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Boto3](https://img.shields.io/badge/Boto3-SDK-yellow)
![IaC](https://img.shields.io/badge/IaC-Python-green)
![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen)

A Python/Boto3 Infrastructure-as-Code (IaC) project that deploys, dynamically scales, and cleanly destroys a secure AWS web architecture using an event-driven automation model.

---

## Overview

This project extends traditional infrastructure provisioning by integrating EventBridge and Lambda to dynamically scale workloads based on predefined schedules.

**Safety mechanisms included:**
- Failed scaling events routed to SQS (Dead Letter Queue)
- Administrative alerts sent via SNS

---

## Architecture

### Architecture Diagram
![Architecture](screenshots/architecture.png)

### High-Level Flow

User Traffic → ALB → Target Group → EC2 (ASG in Private Subnets)  
↑  
Lambda (Scaling Logic)  
↑  
EventBridge (Scheduled Triggers)  
↓  
SQS (Dead Letter Queue) ← Errors → SNS Alerts  

---

## Architecture Breakdown

### Network Layer
- Multi-AZ VPC  
- Public and Private Subnets  
- Internet Gateway  
- NAT Gateways  

### Compute Layer
- Application Load Balancer  
- Target Groups  
- Launch Templates  
- Auto Scaling Group in private subnets  

### Automation Layer
- EventBridge (scheduled triggers)  
- Lambda (scaling logic)  
- SNS (notifications)  
- SQS (dead-letter queue)  

---

## Key Features

### Fault Tolerance & Chaos Testing
- Simulates IAM permission failures  
- Validates full error-handling pipeline  

**Failure flow:**
1. Lambda fails to scale ASG  
2. Error is handled gracefully  
3. Payload pushed to SQS  
4. SNS notification sent  

**Trigger Chaos Test:**
```python
from automation.scale_asg import simulate_iam_failure

simulate_iam_failure()
```

---

### Idempotent Deployment
- Safe re-execution of scripts  
- Prevents duplicate resource creation  

---

### Configuration Management
- Centralized configuration via `config.yaml`  
- Dynamically control infrastructure parameters  

**Sample `config.yaml`:**
```yaml
aws_region: us-east-1
vpc_cidr: 10.0.0.0/16
instance_type: t3.medium
asg_min: 1
asg_max: 3
```

---

### Automated Teardown
- Clean resource deletion using `main_destroy.py`  
- Handles dependency order:
  - Load balancer draining  
  - Gateway detachment  
- Prevents unnecessary AWS costs  

---

## Demonstration

<details>
<summary><strong>Deployment Logs</strong></summary>

Logs sourced from: `screenshots/deployment_logs.txt`

```text
[INFO] Starting AWS infrastructure deployment...
[INFO] VPC created successfully: vpc-0123456789abcdef0
[INFO] Subnets and Routing configured.
[INFO] ASG created and scaling to minimum capacity (1).
[SUCCESS] Deployment complete.
```

</details>

<details>
<summary><strong>Teardown Logs</strong></summary>

Logs sourced from: `screenshots/teardown_logs.txt`

```text
[INFO] Initiating teardown sequence...
[INFO] Draining and deleting Target Groups...
[INFO] Auto Scaling Group deleted.
[INFO] VPC and associated networking components removed.
[SUCCESS] Teardown complete. No orphaned resources.
```

</details>

### Screenshots

**SQS Dead Letter Queue:**  
![SQS DLQ](screenshots/sqs.png)

**SNS Notification:**  
![SNS Alert](screenshots/sns.png)

**Architecture Diagram:**  
![Architecture](screenshots/architecture.png)

---

## Project Structure

```text
aws-autoscale-optimizer/
├── config.yaml
├── main_deploy.py
├── main_destroy.py
│
├── network/
│   ├── CreateNetwork.py
│   └── TearDownNetwork.py
│
├── compute/
│   ├── CreateCompute.py
│   └── TearDownCompute.py
│
├── automation/
│   ├── CreateLambdaEvent.py
│   ├── scale_asg.py
│   └── TearDownLambdaEvent.py
│
├── utils/
│   └── config_loader.py
└── screenshots/
    ├── deployment_logs.txt
    ├── teardown_logs.txt
    ├── sqs.png
    ├── sns.png
    └── architecture.png
```

---

## Getting Started

### Clone Repository

```bash
git clone https://github.com/gandhisiripuram/aws-autoscale-optimizer.git
cd aws-autoscale-optimizer
```

### Setup Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Setup AWS Credentials
Ensure your local environment is authenticated with AWS:

```bash
aws configure
```

Or via environment variables:

```bash
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=us-east-1
```

---

### Configure
Edit `config.yaml` and update:
- AWS region  
- CIDR ranges  
- Scaling parameters  

---

### Deploy

```bash
python main_deploy.py
```

After execution:
- ALB DNS will be printed  
- Access the application via browser  

---

### Destroy

```bash
python main_destroy.py
```

---

## Design Decisions & Trade-offs

While declarative tools like Terraform are standard for Infrastructure-as-Code, this project intentionally uses Python and Boto3 to:

- Gain low-level control over AWS API interactions  
- Understand dependency graphing during teardown  
- Implement imperative state handling  
- Build deeper intuition for AWS service orchestration  

This approach trades off abstraction for control and learning depth.

---

## Skills Demonstrated

### Infrastructure as Code
- AWS automation using Python and Boto3  

### Event-Driven Systems
- Scheduled scaling with EventBridge and Lambda  

### Resilience Engineering
- IAM least privilege design  
- SQS dead-letter queues and SNS alerting  

### Engineering Practices
- Idempotent scripting  
- Modular architecture  
- Dependency-aware teardown  

---