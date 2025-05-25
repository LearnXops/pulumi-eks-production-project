"""
IAM Module for EKS Cluster

This module handles all IAM roles and policies required for the EKS cluster,
including the cluster role, node group role, and any additional service accounts.
"""

import json
import pulumi
import pulumi_aws as aws
from typing import NamedTuple

class IamOutput:
    """
    A class to hold IAM related outputs.
    """
    def __init__(self, cluster_role, node_role, service_account_roles):
        self.cluster_role = cluster_role
        self.node_role = node_role
        self.service_account_roles = service_account_roles

def create_iam_roles(project_name: str) -> IamOutput:
    """
    Create IAM roles and policies for the EKS cluster.
    
    Args:
        project_name: Name of the project for resource naming and tagging
        
    Returns:
        IamOutput: Object containing the created IAM roles
    """
    # EKS Cluster Role
    cluster_role = aws.iam.Role(
        f"{project_name}-cluster-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "eks.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        }),
        tags={
            "Name": f"{project_name}-cluster-role",
            "Project": project_name,
        },
    )
    
    # Attach the Amazon EKS Cluster Policy
    cluster_policy_attachment = aws.iam.RolePolicyAttachment(
        f"{project_name}-cluster-policy",
        role=cluster_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    )
    
    # EKS Node Group Role
    node_role = aws.iam.Role(
        f"{project_name}-node-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        }),
        tags={
            "Name": f"{project_name}-node-role",
            "Project": project_name,
        },
    )
    
    # Attach required policies to node role
    node_policies = [
        "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
        "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
        "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    ]
    
    for i, policy in enumerate(node_policies):
        aws.iam.RolePolicyAttachment(
            f"{project_name}-node-policy-{i}",
            role=node_role.name,
            policy_arn=policy,
        )
    
    # Additional policies for cluster autoscaler
    autoscaler_policy = aws.iam.Policy(
        f"{project_name}-cluster-autoscaler-policy",
        description="Policy for cluster autoscaler",
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "autoscaling:DescribeAutoScalingGroups",
                        "autoscaling:DescribeAutoScalingInstances",
                        "autoscaling:DescribeLaunchConfigurations",
                        "autoscaling:DescribeTags",
                        "autoscaling:SetDesiredCapacity",
                        "autoscaling:TerminateInstanceInAutoScalingGroup",
                        "ec2:DescribeLaunchTemplateVersions"
                    ],
                    "Resource": "*"
                }
            ]
        }),
    )
    
    # Attach autoscaler policy to node role
    aws.iam.RolePolicyAttachment(
        f"{project_name}-autoscaler-policy-attach",
        role=node_role.name,
        policy_arn=autoscaler_policy.arn,
    )
    
    return IamOutput(
        cluster_role=cluster_role,
        node_role=node_role,
        service_account_roles={},  # Can be populated later for service accounts
    )
