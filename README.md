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

Safety mechanisms included:
- Failed scaling events routed to SQS
- Administrative alerts sent via SNS

---

## Architecture

### Architecture Diagram
![Architecture](docs/screenshots/architecture.png)

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

### Fault Tolerance and Chaos Testing
- Simulates IAM permission failures
- Validates error handling pipeline

Failure flow:
1. Lambda fails to scale ASG
2. Error is handled gracefully
3. Payload pushed to SQS
4. SNS notification sent

### Idempotent Deployment
- Safe re-execution of scripts
- Prevents duplicate resource creation

### Configuration Management
- Centralized configuration via `config.yaml`
- Easily modify:
  - CIDR ranges
  - Instance types
  - Scaling schedules

### Automated Teardown
- Clean resource deletion using `main_destroy.py`
- Handles dependencies such as:
  - Load balancer draining
  - Gateway detachment
- Prevents unnecessary AWS costs

---

## Demonstration

<details>
<summary>Deployment Logs</summary>

![Deployment Logs](docs/screenshots/deployment_logs.txt)

</details>

<details>
<summary>Teardown Logs</summary>

![Teardown Logs](docs/screenshots/teardown_logs.txt)

</details>

### Screenshots
**SQS Dead Letter Queue:**  
![SQS DLQ](docs/screenshots/sqs.png)

**SNS Notification:**  
![SNS Alert](docs/screenshots/sns.png)

**Architecture Diagram:**  
![Architecture](docs/screenshots/architecture.png)

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
└── utils/
    └── config_loader.py
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

### Configure
Edit `config.yaml` and set required values:
- AWS region
- CIDR ranges
- Scaling schedules

### Deploy
```bash
python main_deploy.py
```
After execution:
- ALB DNS will be printed
- Access application via browser

### Destroy
```bash
python main_destroy.py
```

---

## Skills Demonstrated

### Infrastructure as Code
- AWS automation using Python and Boto3

### Event-Driven Systems
- Scheduled scaling using EventBridge and Lambda

### Resilience Engineering
- IAM least privilege enforcement
- SQS dead-letter queue and SNS alerting

### Engineering Practices
- Idempotent scripts
- Modular architecture
- Dependency-aware teardown

---