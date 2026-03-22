import boto3
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    cfg = load_config()
    logger = setup_logging("create_network")
    p_name = cfg['project']['name']
    region = cfg['project']['region']
    ec2 = boto3.client("ec2", region_name=region)

    def get_tags(name):
        return [{"Key": "Name", "Value": name}, {"Key": "Project", "Value": p_name}]

    try:
        existing_vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Project", "Values": [p_name]}])["Vpcs"]
        if existing_vpcs:
            logger.warning(f"NOTICE: VPC {existing_vpcs[0]['VpcId']} already exists.")
            logger.info("IDEMPOTENCY ACTION: Network layer is already deployed. Skipping creation.")
            return 
    except Exception as e:
        logger.error(f"FATAL: Failed to check existing VPCs: {e}")
        sys.exit(1)

    try:
        logger.info(f"INTENT: Creating VPC container ({cfg['network']['vpc_cidr']})")
        vpc = ec2.create_vpc(CidrBlock=cfg['network']['vpc_cidr'], TagSpecifications=[{"ResourceType": "vpc", "Tags": get_tags(f"{p_name}-vpc")}])
        vpc_id = vpc['Vpc']['VpcId']
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
        logger.info(f"SUCCESS: Created VPC {vpc_id}")
    except Exception as e:
        logger.error(f"FATAL: VPC Failed: {e}")
        sys.exit(1)

    try:
        logger.info("INTENT: Creating and attaching Internet Gateway")
        igw = ec2.create_internet_gateway(TagSpecifications=[{"ResourceType": "internet-gateway", "Tags": get_tags(f"{p_name}-igw")}])
        igw_id = igw['InternetGateway']['InternetGatewayId']
        ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        logger.info(f"SUCCESS: IGW {igw_id} attached.")
    except Exception as e:
        logger.error(f"FATAL: IGW Failed: {e}")
        sys.exit(1)

    try:
        logger.info("INTENT: Configuring Public Subnets and Route Table")
        public_rt = ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{"ResourceType": "route-table", "Tags": get_tags(f"{p_name}-public-rt")}])['RouteTable']['RouteTableId']
        ec2.create_route(RouteTableId=public_rt, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)

        pub_sub_info = []
        for s_cfg in cfg['network']['public_subnets']:
            sub = ec2.create_subnet(VpcId=vpc_id, CidrBlock=s_cfg['cidr'], AvailabilityZone=s_cfg['az'], TagSpecifications=[{"ResourceType": "subnet", "Tags": get_tags(s_cfg['name'])}])
            s_id = sub['Subnet']['SubnetId']
            ec2.modify_subnet_attribute(SubnetId=s_id, MapPublicIpOnLaunch={'Value': True})
            ec2.create_tags(Resources=[s_id], Tags=[{"Key": "Tier", "Value": "Public"}])
            ec2.associate_route_table(SubnetId=s_id, RouteTableId=public_rt)
            pub_sub_info.append({"id": s_id, "az": s_cfg['az']})
        logger.info("SUCCESS: Public networking initialized.")
    except Exception as e:
        logger.error(f"FATAL: Public Subnet Setup Failed: {e}")
        sys.exit(1)

    try:
        logger.info("INTENT: Creating Highly Available NAT Gateways")
        nat_gws = {}
        for pub_sub in pub_sub_info:
            az = pub_sub["az"]
            s_id = pub_sub["id"]
            eip = ec2.allocate_address(Domain='vpc', TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": get_tags(f"{p_name}-nat-eip-{az}")}])
            nat = ec2.create_nat_gateway(SubnetId=s_id, AllocationId=eip['AllocationId'], TagSpecifications=[{"ResourceType": "natgateway", "Tags": get_tags(f"{p_name}-nat-{az}")}])
            nat_gws[az] = nat['NatGateway']['NatGatewayId']

        logger.info("WAIT: Waiting for NAT availability...")
        ec2.get_waiter('nat_gateway_available').wait(NatGatewayIds=list(nat_gws.values()))
        logger.info("SUCCESS: NAT Gateways provisioned and available.")
    except Exception as e:
        logger.error(f"FATAL: NAT Gateway Creation Failed: {e}")
        sys.exit(1)

    try:
        logger.info("INTENT: Configuring Private Subnets")
        for s_cfg in cfg['network']['private_subnets']:
            az = s_cfg['az']
            nat_id = nat_gws.get(az)
            private_rt = ec2.create_route_table(VpcId=vpc_id, TagSpecifications=[{"ResourceType": "route-table", "Tags": get_tags(f"{p_name}-private-rt-{az}")}])['RouteTable']['RouteTableId']
            ec2.create_route(RouteTableId=private_rt, DestinationCidrBlock='0.0.0.0/0', NatGatewayId=nat_id)
            sub = ec2.create_subnet(VpcId=vpc_id, CidrBlock=s_cfg['cidr'], AvailabilityZone=az, TagSpecifications=[{"ResourceType": "subnet", "Tags": get_tags(s_cfg['name'])}])
            s_id = sub['Subnet']['SubnetId']
            ec2.create_tags(Resources=[s_id], Tags=[{"Key": "Tier", "Value": "Private"}])
            ec2.associate_route_table(SubnetId=s_id, RouteTableId=private_rt)
        logger.info("SUCCESS: Network Foundation Ready.")
    except Exception as e:
        logger.error(f"FATAL: Private Subnet Setup Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()