import boto3
import json
import time
import zipfile
import io
import os
import sys
from botocore.exceptions import ClientError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    config = load_config()
    logger = setup_logging("create_automation")
    project_name = config['project']['name']
    region = config['project']['region']
    
    iam_client = boto3.client("iam", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)
    events_client = boto3.client("events", region_name=region)  
    asg_client = boto3.client("autoscaling", region_name=region)

    def get_tags(name):
        return [{"Key": "Name", "Value": name}, {"Key": "Project", "Value": project_name}]
    
    logger.info(f"INTENT: Discovering target ASG for project '{project_name}'")
    try:
        response = asg_client.describe_auto_scaling_groups(Filters=[{'Name': 'tag:Project', 'Values': [project_name]}])
        if not response['AutoScalingGroups']:
            logger.error("FATAL: Target ASG not found. Cannot attach automation.")
            sys.exit(1)
        asg_name = response['AutoScalingGroups'][0]['AutoScalingGroupName']
        asg_arn = response['AutoScalingGroups'][0]['AutoScalingGroupARN']
        logger.info(f"SUCCESS: Found ASG '{asg_name}'")
    except ClientError as e:
        logger.error(f"FATAL: Discovery failed: {e}")
        sys.exit(1)
    
    role_name = f"{project_name}-lambda-role"
    func_name = f"{project_name}-scheduler"

    logger.info(f"INTENT: Configuring IAM Role '{role_name}' and Policies")
    trust_policy_dict = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}   
    try:
        role_arn = iam_client.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy_dict), Tags=get_tags(role_name))['Role']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            role_arn = iam_client.get_role(RoleName=role_name)['Role']['Arn']
        else:
            logger.error(f"FATAL: IAM Role creation failed: {e}")
            sys.exit(1) 

    inline_policy_dict = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["autoscaling:UpdateAutoScalingGroup"], "Resource": asg_arn},
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:*:*:*"},
            {"Effect": "Allow", "Action": ["sns:Publish"], "Resource": "arn:aws:sns:us-east-1:590157535724:asg-alerts-topic"},
            {"Effect": "Allow", "Action": ["sqs:SendMessage"], "Resource": "arn:aws:sqs:us-east-1:590157535724:asg-task-queue"}
        ]
    }
    
    try:
        iam_client.put_role_policy(RoleName=role_name, PolicyName=f"{project_name}-scaling-policy", PolicyDocument=json.dumps(inline_policy_dict))
    except ClientError as e:
        logger.warning(f"WAIT: Policy attach delayed: {e}")

    logger.info("WAIT: Allowing IAM role propagation (15s)...")
    time.sleep(15)
    logger.info("SUCCESS: IAM permissions ready.")

    logger.info(f"INTENT: Packaging and deploying Lambda function '{func_name}'")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(base_dir, "scale_asg.py"), arcname='scale_asg.py')
    zip_buffer.seek(0)  
    zip_bytes = zip_buffer.read()

    try:
        func_arn = lambda_client.create_function(FunctionName=func_name, Runtime='python3.11', Role=role_arn, Handler='scale_asg.lambda_handler', Code={'ZipFile': zip_bytes}, Tags={'Name': func_name, 'Project': project_name})['FunctionArn']
        logger.info("SUCCESS: Lambda function deployed.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            logger.info("IDEMPOTENCY ACTION: Updating existing Lambda code...")
            lambda_client.update_function_code(FunctionName=func_name, ZipFile=zip_bytes)
            func_arn = lambda_client.get_function(FunctionName=func_name)['Configuration']['FunctionArn']
        else:
            logger.error(f"FATAL: Lambda deployment failed: {e}")
            sys.exit(1)

    logger.info("INTENT: Configuring EventBridge Scheduler Rules")
    m_cfg = config['automation']['morning_shift']
    e_cfg = config['automation']['evening_shift']

    try:
        m_rule_arn = events_client.put_rule(Name=f"{project_name}-morning-rule", ScheduleExpression=m_cfg['cron'], State='ENABLED', Tags=get_tags(f"{project_name}-morning-rule"))['RuleArn']
        e_rule_arn = events_client.put_rule(Name=f"{project_name}-evening-rule", ScheduleExpression=e_cfg['cron'], State='ENABLED', Tags=get_tags(f"{project_name}-evening-rule"))['RuleArn']
    except ClientError as e:
        logger.error(f"FATAL: EventBridge rule creation failed: {e}")
        sys.exit(1)

    try:
        lambda_client.add_permission(FunctionName=func_name, StatementId='MorningEventInvokeLambda', Action='lambda:InvokeFunction', Principal='events.amazonaws.com', SourceArn=m_rule_arn)              
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            pass 
        else:
            logger.error(f"FATAL: Failed to attach Morning trigger permission: {e}")
            sys.exit(1)
            
    try:
        lambda_client.add_permission(FunctionName=func_name, StatementId='EveningEventInvokeLambda', Action='lambda:InvokeFunction', Principal='events.amazonaws.com', SourceArn=e_rule_arn)              
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            pass 
        else:
            logger.error(f"FATAL: Failed to attach Evening trigger permission: {e}")
            sys.exit(1)

    try:
        logger.info("IDEMPOTENCY ACTION: Updating EventBridge Targets with Config Payloads...")
        events_client.put_targets(Rule=f"{project_name}-morning-rule", Targets=[{'Id': 'MorningTarget1', 'Arn': func_arn, 'Input': json.dumps({"asg_name": asg_name, "min_size": m_cfg['min_size'], "max_size": m_cfg['max_size'], "desired_capacity": m_cfg['desired_capacity']})}])
        events_client.put_targets(Rule=f"{project_name}-evening-rule", Targets=[{'Id': 'EveningTarget1', 'Arn': func_arn, 'Input': json.dumps({"asg_name": asg_name, "min_size": e_cfg['min_size'], "max_size": e_cfg['max_size'], "desired_capacity": e_cfg['desired_capacity']})}])
        logger.info("SUCCESS: Automation layer successfully synced with config.yaml!")
    except ClientError as e:
        logger.error(f"FATAL: Failed to attach targets to rules: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()