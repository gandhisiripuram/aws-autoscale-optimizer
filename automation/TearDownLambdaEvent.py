import boto3
import os
import sys
from botocore.exceptions import ClientError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    config = load_config()
    logger = setup_logging("destroy_automation")
    project_name = config['project']['name']
    region = config['project']['region']
    
    iam_client = boto3.client("iam", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)
    events_client = boto3.client("events", region_name=region)  
    logs_client = boto3.client("logs", region_name=region)

    role_name = f"{project_name}-lambda-role"
    func_name = f"{project_name}-scheduler"
    morning_rule_name = f"{project_name}-morning-rule"
    evening_rule_name = f"{project_name}-evening-rule"
    log_group_name = f"/aws/lambda/{func_name}"

    logger.info("INTENT: Detaching targets and deleting EventBridge cron rules")
    try:
        response = events_client.remove_targets(Rule=morning_rule_name, Ids=['MorningTarget1'])
        if response.get('FailedEntryCount', 0) == 0:
            events_client.delete_rule(Name=morning_rule_name)
            logger.info(f"SUCCESS: Rule {morning_rule_name} deleted.")
        else:
            logger.error(f"FATAL: Failed to remove morning target: {response['FailedEntries'][0]['ErrorMessage']}") 
    except ClientError as e: 
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"NOTICE: {morning_rule_name} already deleted.")
        else:
            logger.error(f"FATAL: {morning_rule_name} Error: {e}")

    try:
        response = events_client.remove_targets(Rule=evening_rule_name, Ids=['EveningTarget1'])
        if response.get('FailedEntryCount', 0) == 0:
            events_client.delete_rule(Name=evening_rule_name)
            logger.info(f"SUCCESS: Rule {evening_rule_name} deleted.")
        else:
            logger.error(f"FATAL: Failed to remove evening target: {response['FailedEntries'][0]['ErrorMessage']}") 
    except ClientError as e: 
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"NOTICE: {evening_rule_name} already deleted.")
        else:
            logger.error(f"FATAL: {evening_rule_name} Error: {e}")

    logger.info("INTENT: Destroying Lambda function and Log Groups") 
    try:
        lambda_client.delete_function(FunctionName=func_name)
        logger.info(f"SUCCESS: Lambda function {func_name} deleted.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"NOTICE: {func_name} already deleted.")
        else:
            logger.error(f"FATAL: Lambda Error: {e}")

    try:
        logs_client.delete_log_group(logGroupName=log_group_name)
        logger.info(f"SUCCESS: Log group {log_group_name} deleted.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"NOTICE: {log_group_name} already deleted.")
        else:
            logger.error(f"FATAL: Log Group Error: {e}")

    logger.info(f"INTENT: Detaching policies and deleting IAM Role '{role_name}'")
    policy_name = f"{project_name}-scaling-policy"
    try:
        iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        logger.info(f"SUCCESS: Policy {policy_name} deleted.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity': 
            logger.warning(f"NOTICE: Policy {policy_name} already deleted.")
        else:
            logger.error(f"FATAL: Policy Error: {e}")

    try:
        iam_client.delete_role(RoleName=role_name)
        logger.info(f"SUCCESS: Role {role_name} deleted.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            logger.warning(f"NOTICE: Role {role_name} already deleted.")
        else:
            logger.error(f"FATAL: Role Error: {e}")

if __name__ == "__main__":
    main()