"""
Main entry point for the Pulumi EKS project.
This module initializes the Pulumi stack and orchestrates the deployment
of all infrastructure components.
"""
import json
import os
from pathlib import Path
import pulumi

# Import infrastructure modules
from infrastructure.vpc import create_vpc
from infrastructure.eks import create_eks_cluster
from infrastructure.iam import create_iam_roles
from infrastructure.addons import setup_addons

def load_eks_config() -> dict:
    """Load EKS configuration from JSON file.
    
    Returns:
        dict: Parsed JSON configuration
    """
    # First try environment-specific config, fall back to default
    env = os.environ.get('ENV', 'dev')
    config_paths = [
        Path(__file__).parent / 'config' / f'eks-config.{env}.json',
        Path(__file__).parent / 'config' / 'eks-config.json'
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    
    raise FileNotFoundError("No EKS config file found. Expected one of: " + ", ".join(str(p) for p in config_paths))

def main():
    """
    Main function that defines and creates the Pulumi stack.
    """
    # Load configuration
    config = pulumi.Config()
    eks_config = load_eks_config()
    
    # Get project name from config
    project_name = eks_config["project"]["name"]
    
    # Create VPC
    vpc = create_vpc(project_name)
    
    # Create IAM roles
    roles = create_iam_roles(project_name)
    
    # Create EKS cluster
    cluster = create_eks_cluster(
        project_name=project_name,
        vpc_id=vpc.vpc_id,
        private_subnet_ids=vpc.private_subnet_ids,
        public_subnet_ids=vpc.public_subnet_ids,
        node_role_arn=roles.node_role.arn,
        node_config=eks_config["eks"]["node"]
    )
    
    # Set up add-ons if enabled
    addons_config = eks_config["eks"].get("addons", {})
    if addons_config.get("enable", True):
        aws_region = config.require("aws-region")
        
        # Get Karpenter configuration if enabled
        karpenter_config = None
        if addons_config.get("karpenter", False):
            karpenter_config = eks_config.get("karpenter", {})
        
        setup_addons(
            kubeconfig=cluster.kubeconfig,
            project_name=project_name,
            aws_region=aws_region,
            addons_config=addons_config,
            cluster_name=cluster.eks_cluster.name,
            vpc_id=vpc.vpc_id,
            karpenter_config=karpenter_config
        )
    
    # Export values
    pulumi.export('kubeconfig', cluster.kubeconfig)
    pulumi.export('cluster_name', cluster.eks_cluster.name)
    pulumi.export('vpc_id', vpc.vpc_id)

if __name__ == "__main__":
    main()
