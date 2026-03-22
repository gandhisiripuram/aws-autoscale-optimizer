import boto3
import os
import sys
import time
from botocore.exceptions import ClientError
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_loader import load_config, setup_logging

def main():
    cfg = load_config()
    logger = setup_logging("destroy_network")
    p_name = cfg['project']['name']
    region = cfg['project']['region']
    ec2 = boto3.client("ec2", region_name=region)

    try:
        vpc_res = ec2.describe_vpcs(Filters=[{'Name': 'tag:Project', 'Values': [p_name]}])['Vpcs']
        if not vpc_res:
            logger.warning("NOTICE: No VPC found. Skipping Network teardown.")
            return
            
        vid = vpc_res[0]['VpcId']

        try:
            logger.info("INTENT: Deleting NAT Gateways and releasing EIPs")
            nats = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vid]}])['NatGateways']
            for n in nats:
                if n['State'] != 'deleted': 
                    ec2.delete_nat_gateway(NatGatewayId=n['NatGatewayId'])
                    
            while True:
                active = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vid]}])['NatGateways']
                if all(a['State'] == 'deleted' for a in active): 
                    break
                logger.info("WAIT: NAT Gateways deleting...")
                time.sleep(20)
            
            eips = ec2.describe_addresses(Filters=[{'Name': 'tag:Project', 'Values': [p_name]}])['Addresses']
            for eip in eips: 
                ec2.release_address(AllocationId=eip['AllocationId'])
                
            logger.info("SUCCESS: NAT Gateways and EIPs released.")
        except Exception as e:
            logger.warning(f"NOTICE: NAT Cleanup issue: {e}")

        try:
            logger.info("INTENT: Deleting Custom Route Tables")
            rts = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vid]}])['RouteTables']
            for rt in rts:
                is_main = any(assoc.get('Main', False) for assoc in rt.get('Associations', []))
                if not is_main:
                    for assoc in rt.get('Associations', []):
                        ec2.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
                    ec2.delete_route_table(RouteTableId=rt['RouteTableId'])
            logger.info("SUCCESS: Custom Route Tables deleted.")
        except Exception as e:
            logger.warning(f"NOTICE: Route Table Cleanup issue: {e}")

        try:
            logger.info("INTENT: Deleting Subnets")
            subs = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vid]}])['Subnets']
            for s in subs:
                for i in range(10):
                    try:
                        ec2.delete_subnet(SubnetId=s['SubnetId'])
                        break
                    except ClientError:
                        time.sleep(10)
            logger.info("SUCCESS: All Subnets deleted.")
        except Exception as e:
            logger.warning(f"NOTICE: Subnet Cleanup issue: {e}")

        try:
            logger.info("INTENT: Detaching IGW and deleting VPC")
            igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vid]}])['InternetGateways']
            for igw in igws:
                ec2.detach_internet_gateway(InternetGatewayId=igw['InternetGatewayId'], VpcId=vid)
                ec2.delete_internet_gateway(InternetGatewayId=igw['InternetGatewayId'])
            
            for i in range(15):
                try:
                    ec2.delete_vpc(VpcId=vid)
                    logger.info("SUCCESS: Network Infrastructure fully removed.")
                    break
                except ClientError as e:
                    logger.info("WAIT: VPC busy resolving dependencies. Retrying...")
                    time.sleep(20)
        except Exception as e:
            logger.error(f"FATAL: VPC Final Deletion Failed: {e}")

    except Exception as e:
        logger.error(f"FATAL: Network destroy failed: {e}")

if __name__ == "__main__":
    main()