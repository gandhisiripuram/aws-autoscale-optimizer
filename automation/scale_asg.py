import boto3
import logging
import json
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_config = Config(read_timeout=3, connect_timeout=3, retries={'max_attempts': 2})

asg_client = boto3.client('autoscaling', config=lambda_config)
sns_client = boto3.client('sns', region_name='us-east-1')
sqs_client = boto3.client('sqs', region_name='us-east-1')

SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:590157535724:asg-alerts-topic"
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/590157535724/asg-task-queue"

def lambda_handler(event, context):
    asg_name = event.get("asg_name")
    min_size = event.get("min_size")
    max_size = event.get("max_size")
    desired_capacity = event.get("desired_capacity")
    
    if not asg_name or min_size is None or max_size is None or desired_capacity is None:
        logger.error(f"FATAL: Missing parameters in payload: {event}")
        return {"statusCode": 400, "body": "Invalid payload"}

    logger.info(f"INTENT: Updating ASG {asg_name} to Min:{min_size}, Max:{max_size}, Desired:{desired_capacity}")
    
    try:
        target_asg = "fake-asg-for-testing" if event.get("chaos_test") else asg_name

        response = asg_client.update_auto_scaling_group(
            AutoScalingGroupName=target_asg, 
            MinSize=min_size,
            MaxSize=max_size,
            DesiredCapacity=desired_capacity
        )
        
        logger.info("SUCCESS: Auto Scaling Group updated.")
        return {"statusCode": 200, "body": "ASG successfully scaled"}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']  
        full_error = f"[{error_code}]: {error_msg}"
        logger.error(f"FATAL: ASG Update failed {full_error}")
        
        logger.info("Triggering Safety Net (SNS Alert + SQS Redrive)...")
        
        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="ASG Optimizer Alert - Task Failed",
                Message=f"Failed to update ASG '{target_asg}'.\n\nError: {full_error}\nTime: {datetime.now()}"
            )
            logger.info("SNS Alert sent.")
        except Exception as sns_err:
            logger.error(f"Failed to send SNS: {sns_err}")

        failed_payload = {
            "asg_name": target_asg,
            "min_size": min_size,
            "max_size": max_size,
            "desired_capacity": desired_capacity,
            "error_reason": full_error,
            "timestamp": str(datetime.now())
        }
        
        try:
            sqs_client.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(failed_payload))
            logger.info("Failed task pushed to SQS Queue.")
        except Exception as sqs_err:
            logger.error(f"Failed to push to SQS: {sqs_err}")

        return {"statusCode": 500, "body": "Task failed. Routed to Safety Net."}