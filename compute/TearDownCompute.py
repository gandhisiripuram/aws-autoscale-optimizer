import boto3
import os
import sys
import time
from botocore.exceptions import ClientError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    cfg = load_config()
    logger = setup_logging("destroy_compute")
    p_name = cfg['project']['name']
    region = cfg['project']['region']
    
    ec2 = boto3.client("ec2", region_name=region)
    elbv2 = boto3.client("elbv2", region_name=region)
    asg = boto3.client("autoscaling", region_name=region)

    try:
        logger.info(f"INTENT: Deleting Auto Scaling Group '{p_name}-asg'")
        asg.delete_auto_scaling_group(AutoScalingGroupName=f"{p_name}-asg", ForceDelete=True)
        while True:
            response = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[f"{p_name}-asg"])
            if not response["AutoScalingGroups"]: 
                break
            logger.info("WAIT: Waiting for EC2 Instances to terminate...")
            time.sleep(20)
        logger.info("SUCCESS: Auto Scaling Group removed.")
    except ClientError as e: 
        if 'ValidationError' in str(e):
            logger.warning("NOTICE: ASG already removed.")
        else:
            logger.error(f"FATAL: ASG Error: {e}")

    try:
        logger.info("INTENT: Deleting Load Balancer and Target Group")
        albs = elbv2.describe_load_balancers(Names=[f"{p_name[:24]}-alb"])["LoadBalancers"]
        if albs:
            alb_arn = albs[0]["LoadBalancerArn"]
            elbv2.delete_load_balancer(LoadBalancerArn=alb_arn)
            logger.info("WAIT: Waiting for Load Balancer to finish draining...")
            elbv2.get_waiter('load_balancers_deleted').wait(LoadBalancerArns=[alb_arn])
        
        tgs = elbv2.describe_target_groups(Names=[f"{p_name[:24]}-tg"])["TargetGroups"]
        if tgs:
            tg_arn = tgs[0]["TargetGroupArn"]
            for i in range(15):
                try:
                    elbv2.delete_target_group(TargetGroupArn=tg_arn)
                    break
                except ClientError as e:
                    if 'ResourceInUse' in str(e):
                        logger.info("WAIT: Target Group locked by terminating listener. Retrying...")
                        time.sleep(15)
                    else:
                        raise e
        logger.info("SUCCESS: ALB and Target Group released.")
    except ClientError as e: 
        if 'LoadBalancerNotFound' in str(e) or 'TargetGroupNotFound' in str(e):
            logger.warning("NOTICE: ALB/TG already removed.")
        else:
            logger.error(f"FATAL: ALB/TG Error: {e}")

    try:
        logger.info("INTENT: Removing Security Groups and sweeping Orphan ENIs")
        sgs = ec2.describe_security_groups(Filters=[{"Name": "tag:Project", "Values": [p_name]}])["SecurityGroups"]
        
        for sg in sgs:
            if sg.get('IpPermissions'):
                ec2.revoke_security_group_ingress(GroupId=sg['GroupId'], IpPermissions=sg['IpPermissions'])
            if sg.get('IpPermissionsEgress'):
                ec2.revoke_security_group_egress(GroupId=sg['GroupId'], IpPermissions=sg['IpPermissionsEgress'])

        for sg in sgs:
            for i in range(15):
                try:
                    ec2.delete_security_group(GroupId=sg["GroupId"])
                    break
                except ClientError as e:
                    if 'DependencyViolation' in str(e):
                        logger.warning(f"WAIT: Elastic Network Interfaces blocking SG {sg['GroupId']}. Retrying...")
                        time.sleep(20)
                    else:
                        logger.error(f"FATAL: SG Deletion Error: {e}")
                        break
        logger.info("SUCCESS: Security Groups deleted.")
    except Exception as e:
        logger.error(f"FATAL: Security Group Phase Failed: {e}")

    try:
        logger.info("INTENT: Deleting Launch Template")
        ec2.delete_launch_template(LaunchTemplateName=f"{p_name}-lt")
        logger.info("SUCCESS: Launch Template deleted.")
    except ClientError as e:
        if 'InvalidLaunchTemplateName.NotFoundException' in str(e) or 'InvalidLaunchTemplateName.NotFound' in str(e):
            logger.warning("NOTICE: Launch Template already removed.")
        else:
            logger.error(f"FATAL: Launch Template Error: {e}")

if __name__ == "__main__":
    main()