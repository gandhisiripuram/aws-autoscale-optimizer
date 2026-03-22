import boto3
import os
import sys
import base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    cfg = load_config()
    logger = setup_logging("create_compute")
    p_name = cfg['project']['name']
    region = cfg['project']['region']
    
    ec2 = boto3.client("ec2", region_name=region)
    elbv2 = boto3.client("elbv2", region_name=region)
    asg = boto3.client("autoscaling", region_name=region)
    ssm = boto3.client("ssm", region_name=region)

    try:
        existing_asgs = asg.describe_auto_scaling_groups(Filters=[{"Name": "tag:Project", "Values": [p_name]}])["AutoScalingGroups"]
        if existing_asgs:
            asg_name = existing_asgs[0]["AutoScalingGroupName"]
            logger.warning(f"NOTICE: Compute layer already exists ({asg_name}).")
            logger.info("IDEMPOTENCY ACTION: Updating existing ASG base capacities from config...")
            asg.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                MinSize=cfg['compute']['asg_min'],
                MaxSize=cfg['compute']['asg_max'],
                DesiredCapacity=cfg['compute']['asg_desired']
            )
            logger.info("SUCCESS: Existing ASG updated. Skipping full compute creation.")
            return 
    except Exception as e:
        logger.error(f"FATAL: Idempotency check failed: {e}")
        sys.exit(1)

    logger.info("INTENT: Discovering Network Foundation (VPC & Subnets)")
    try:
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Project", "Values": [p_name]}])["Vpcs"]
        vpc_id = vpcs[0]["VpcId"]
        
        pub_subs = [s["SubnetId"] for s in ec2.describe_subnets(Filters=[{"Name": "tag:Project", "Values": [p_name]}, {"Name": "tag:Tier", "Values": ["Public"]}])["Subnets"]]
        pvt_subs = [s["SubnetId"] for s in ec2.describe_subnets(Filters=[{"Name": "tag:Project", "Values": [p_name]}, {"Name": "tag:Tier", "Values": ["Private"]}])["Subnets"]]
        
        if len(pub_subs) < 2 or len(pvt_subs) < 2:
            logger.error("FATAL: Environment corrupted. Compute layer requires at least 2 Public and 2 Private subnets.")
            sys.exit(1)
            
        logger.info(f"SUCCESS: Discovered VPC {vpc_id} with required subnets.")
    except Exception as e:
        logger.error(f"FATAL: Discovery or Validation Failed: {e}")
        sys.exit(1)

    logger.info("INTENT: Creating Security Groups for ALB and Web Tier")
    try:
        alb_sg = ec2.create_security_group(Description="ALB SG", GroupName=f"{p_name}-alb-sg", VpcId=vpc_id, TagSpecifications=[{"ResourceType": "security-group", "Tags": [{"Key": "Project", "Value": p_name}]}])["GroupId"]
        ec2.authorize_security_group_ingress(GroupId=alb_sg, IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])
        web_sg = ec2.create_security_group(Description="Web SG", GroupName=f"{p_name}-web-sg", VpcId=vpc_id, TagSpecifications=[{"ResourceType": "security-group", "Tags": [{"Key": "Project", "Value": p_name}]}])["GroupId"]
        ec2.authorize_security_group_ingress(GroupId=web_sg, IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'UserIdGroupPairs': [{'GroupId': alb_sg}]}])
        logger.info("SUCCESS: Security Groups created and rules attached.")
    except Exception as e:
        logger.error(f"FATAL: Security Group creation failed: {e}")
        sys.exit(1)

    logger.info("INTENT: Provisioning Application Load Balancer and Target Group")
    try:
        tg_arn = elbv2.create_target_group(Name=f"{p_name[:24]}-tg", Protocol='HTTP', Port=80, VpcId=vpc_id, TargetType='instance')["TargetGroups"][0]["TargetGroupArn"]
        elbv2.add_tags(ResourceArns=[tg_arn], Tags=[{"Key": "Project", "Value": p_name}])
        alb = elbv2.create_load_balancer(Name=f"{p_name[:24]}-alb", Subnets=pub_subs, SecurityGroups=[alb_sg])["LoadBalancers"][0]
        elbv2.create_listener(LoadBalancerArn=alb["LoadBalancerArn"], Protocol='HTTP', Port=80, DefaultActions=[{'Type': 'forward', 'TargetGroupArn': tg_arn}])
        
        logger.info("WAIT: Waiting for Load Balancer to become active...")
        elbv2.get_waiter('load_balancer_available').wait(LoadBalancerArns=[alb["LoadBalancerArn"]])
        logger.info("SUCCESS: ALB and Target Group are active.")
    except Exception as e:
        logger.error(f"FATAL: ALB Provisioning failed: {e}")
        sys.exit(1)

    logger.info("INTENT: Deploying Launch Template and Auto Scaling Group")
    try:
        ami_id = ssm.get_parameter(Name=cfg['compute']['ami_ssm_path'])["Parameter"]["Value"]
        ud = base64.b64encode(f"#!/bin/bash\nyum install -y httpd\nsystemctl start httpd\nsystemctl enable httpd\necho '<h1>Project: {p_name}</h1>' > /var/www/html/index.html\n".encode()).decode()
        
        ec2.create_launch_template(LaunchTemplateName=f"{p_name}-lt", LaunchTemplateData={'ImageId': ami_id, 'InstanceType': cfg['compute']['instance_type'], 'SecurityGroupIds': [web_sg], 'UserData': ud})
        
        asg.create_auto_scaling_group(
            AutoScalingGroupName=f"{p_name}-asg",
            LaunchTemplate={'LaunchTemplateName': f"{p_name}-lt", 'Version': '$Latest'},
            MinSize=cfg['compute']['asg_min'], 
            MaxSize=cfg['compute']['asg_max'], 
            DesiredCapacity=cfg['compute']['asg_desired'],
            VPCZoneIdentifier=",".join(pvt_subs), 
            TargetGroupARNs=[tg_arn], 
            HealthCheckType='ELB',
            Tags=[{'ResourceId': f"{p_name}-asg", 'ResourceType': 'auto-scaling-group', 'Key': 'Project', 'Value': p_name, 'PropagateAtLaunch': True}]
        )
        logger.info(f"SUCCESS: Compute layer live! Site accessible at http://{alb['DNSName']}")
    except Exception as e:
        logger.error(f"FATAL: ASG Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()