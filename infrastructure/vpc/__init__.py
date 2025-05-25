"""
VPC Module for EKS Cluster

This module provides functionality to create a production-grade VPC with public and private subnets,
NAT gateways, and proper route tables for an EKS cluster.
"""

import pulumi
import pulumi_aws as aws
class VpcOutput:
    """
    A class to hold VPC related outputs.
    """
    def __init__(self, vpc_id, private_subnet_ids, public_subnet_ids):
        self.vpc_id = vpc_id
        self.private_subnet_ids = private_subnet_ids
        self.public_subnet_ids = public_subnet_ids

import pulumi
import pulumi_aws as aws
from typing import List

def create_vpc(project_name: str) -> VpcOutput:
    """
    Create a production-ready VPC with public and private subnets for EKS.
    Args:
        project_name: Name for tagging AWS resources
    Returns:
        VpcOutput: Object containing VPC ID and subnet IDs
    """
    # 1. Create VPC
    vpc = aws.ec2.Vpc(
        f"{project_name}-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={"Name": f"{project_name}-vpc", "Project": project_name}
    )

    # 2. Create Internet Gateway
    igw = aws.ec2.InternetGateway(
        f"{project_name}-igw",
        vpc_id=vpc.id,
        tags={"Name": f"{project_name}-igw", "Project": project_name}
    )

    # 3. Get availability zones (use 2 for HA)
    azs = aws.get_availability_zones(state="available").names[:2]

    # 4. Create public and private subnets
    public_subnets = []
    private_subnets = []
    for i, az in enumerate(azs):
        public_subnets.append(
            aws.ec2.Subnet(
                f"{project_name}-public-{i}",
                vpc_id=vpc.id,
                cidr_block=f"10.0.{i}.0/24",
                availability_zone=az,
                map_public_ip_on_launch=True,
                tags={"Name": f"{project_name}-public-{i}", "Project": project_name}
            )
        )
        private_subnets.append(
            aws.ec2.Subnet(
                f"{project_name}-private-{i}",
                vpc_id=vpc.id,
                cidr_block=f"10.0.{i+10}.0/24",
                availability_zone=az,
                map_public_ip_on_launch=False,
                tags={"Name": f"{project_name}-private-{i}", "Project": project_name}
            )
        )

    # 5. Create public route table and associate with public subnets
    public_rt = aws.ec2.RouteTable(
        f"{project_name}-public-rt",
        vpc_id=vpc.id,
        routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
        tags={"Name": f"{project_name}-public-rt", "Project": project_name}
    )
    for i, subnet in enumerate(public_subnets):
        aws.ec2.RouteTableAssociation(
            f"{project_name}-public-rta-{i}",
            subnet_id=subnet.id,
            route_table_id=public_rt.id
        )

    # 6. Create NAT Gateway in the first public subnet
    eip = aws.ec2.Eip(f"{project_name}-nat-eip", domain="vpc")
    nat_gw = aws.ec2.NatGateway(
        f"{project_name}-natgw",
        allocation_id=eip.id,
        subnet_id=public_subnets[0].id,
        tags={"Name": f"{project_name}-natgw", "Project": project_name}
    )

    # 7. Private route table with NAT
    private_rt = aws.ec2.RouteTable(
        f"{project_name}-private-rt",
        vpc_id=vpc.id,
        routes=[{"cidr_block": "0.0.0.0/0", "nat_gateway_id": nat_gw.id}],
        tags={"Name": f"{project_name}-private-rt", "Project": project_name}
    )
    for i, subnet in enumerate(private_subnets):
        aws.ec2.RouteTableAssociation(
            f"{project_name}-private-rta-{i}",
            subnet_id=subnet.id,
            route_table_id=private_rt.id
        )

    # 8. S3 VPC Endpoint for private subnets
    aws.ec2.VpcEndpoint(
        f"{project_name}-s3-endpoint",
        vpc_id=vpc.id,
        service_name=f"com.amazonaws.{aws.config.region}.s3",
        vpc_endpoint_type="Gateway",
        route_table_ids=[private_rt.id],
        tags={"Name": f"{project_name}-s3-endpoint", "Project": project_name}
    )

    return VpcOutput(
        vpc_id=vpc.id,
        private_subnet_ids=[s.id for s in private_subnets],
        public_subnet_ids=[s.id for s in public_subnets],
    )

