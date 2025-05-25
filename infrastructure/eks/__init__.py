"""
EKS Cluster Module

This module handles the creation and configuration of an Amazon EKS cluster,
including the control plane, node groups, and Fargate profiles.
"""

from typing import Dict, List, Optional
import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
from pulumi_aws.ec2 import SecurityGroup, SecurityGroupRule, SecurityGroupRuleArgs

class EksOutput:
    """
    A class to hold EKS cluster related outputs.
    """
    def __init__(self, kubeconfig, eks_cluster, node_groups, oidc_provider_id=None):
        self.kubeconfig = kubeconfig
        self.eks_cluster = eks_cluster
        self.node_groups = node_groups
        self.oidc_provider_id = oidc_provider_id

def create_eks_cluster(
    project_name: str,
    vpc_id: str,
    private_subnet_ids: List[str],
    public_subnet_ids: List[str],
    node_role_arn: pulumi.Output[str],
    node_config: dict,
) -> EksOutput:
    """
    Create an EKS cluster with managed node groups.
    
    Args:
        project_name: Name of the project for resource naming and tagging
        vpc_id: ID of the VPC where the cluster will be created
        private_subnet_ids: List of private subnet IDs for the cluster
        public_subnet_ids: List of public subnet IDs for the cluster
        node_role_arn: ARN of the IAM role for the EKS nodes
        
    Returns:
        EksOutput: Object containing cluster and node group information
    """
    # Node config is now passed as a parameter
    
    # Create an EKS cluster
    cluster = eks.Cluster(
        f"{project_name}-cluster",
        name=f"{project_name}-cluster",
        vpc_id=vpc_id,
        subnet_ids=private_subnet_ids + public_subnet_ids,
        create_oidc_provider=True,
        enabled_cluster_log_types=[
            "api", "audit", "authenticator", "controllerManager", "scheduler"
        ],
        tags={
            "Name": f"{project_name}-cluster",
            "Project": project_name,
            "Environment": "production",
        },
        # Enable private endpoint and public access
        endpoint_private_access=True,
        endpoint_public_access=True,
        public_access_cidrs=["0.0.0.0/0"],  # Restrict in production
        # Configure cluster security group
        cluster_security_group=aws.ec2.SecurityGroup(
            f"{project_name}-cluster-sg",
            vpc_id=vpc_id,
            description="EKS Cluster Security Group",
            ingress=[
                {
                    "description": "Allow nodes to communicate with each other",
                    "from_port": 0,
                    "to_port": 0,
                    "protocol": "-1",
                    "cidr_blocks": ["172.20.0.0/16"],
                },
                {
                    "description": "Allow pods to communicate with the cluster API",
                    "from_port": 443,
                    "to_port": 443,
                    "protocol": "tcp",
                    "cidr_blocks": ["0.0.0.0/0"],
                },
            ],
            egress=[
                {
                    "description": "Allow all outbound traffic",
                    "from_port": 0,
                    "to_port": 0,
                    "protocol": "-1",
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ],
            tags={
                "Name": f"{project_name}-cluster-sg",
                "Project": project_name,
            },
        ),
    )

    # Create managed node group using config
    node_group = aws.eks.NodeGroup(
        f"{project_name}-ng",
        cluster_name=cluster.core.cluster.name,
        node_role_arn=node_role_arn,
        subnet_ids=private_subnet_ids,
        scaling_config={
            "desired_size": node_config.get("desiredSize", 2),
            "min_size": node_config.get("minSize", 2),
            "max_size": node_config.get("maxSize", 5),
        },
        instance_types=[node_config.get("instanceType", "t3.medium")],
        tags={
            "Name": f"{project_name}-ng",
            "Project": project_name,
            "k8s.io/cluster-autoscaler/enabled": "true",
            "k8s.io/cluster-autoscaler/auto-discovery": "enabled",
        },
    )

    # Get the OIDC provider ID from the cluster's OIDC provider URL
    oidc_provider_id = cluster.core.oidc_provider.url.apply(lambda url: url.split('/')[-1])
    return EksOutput(
        kubeconfig=cluster.kubeconfig,
        eks_cluster=cluster,
        node_groups={"default": node_group},
        oidc_provider_id=oidc_provider_id
    )
