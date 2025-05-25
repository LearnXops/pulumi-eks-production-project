"""
Kubernetes Add-ons Module

This module handles the installation and configuration of essential Kubernetes add-ons
for the EKS cluster, including:
- Metrics Server
- AWS EBS CSI Driver
- Karpenter
"""

import json
import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi_kubernetes.core.v1 import Namespace, ServiceAccount
from pulumi_kubernetes.yaml import ConfigGroup
from pulumi_kubernetes.apiextensions import CustomResource
from pulumi_kubernetes.meta.v1 import ObjectMetaArgs
from pulumi_kubernetes.provider import Provider

def setup_addons(
    kubeconfig: pulumi.Output[str], 
    project_name: str, 
    aws_region: str,
    addons_config: dict,
    cluster_name: str,
    vpc_id: str,
    karpenter_config: dict = None,
    oidc_provider_id: str = None,
    cluster_endpoint=None,
    cluster_ca=None
) -> None:
    """Install all configured Kubernetes add-ons for the EKS cluster.
    
    Args:
        kubeconfig: The kubeconfig for the EKS cluster
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
        addons_config: Configuration for the add-ons to install
        cluster_name: Name of the EKS cluster
        vpc_id: The VPC ID where the EKS cluster is deployed
        karpenter_config: Configuration for Karpenter (optional)
    """
    # Create a Kubernetes provider instance
    k8s_provider = k8s.Provider(
        "k8s-provider",
        kubeconfig=kubeconfig,
        enable_server_side_apply=True
    )
    
    # Install Metrics Server (enabled by default)
    if addons_config.get("metricsServer", True):
        _install_metrics_server(k8s_provider, project_name)
    
    # Install AWS EBS CSI Driver if enabled
    if addons_config.get("ebsCsiDriver", True):
        _install_ebs_csi_driver(k8s_provider, project_name, aws_region)
    
    # Install Karpenter if enabled
    if addons_config.get("karpenter", False) and karpenter_config:
        _install_karpenter(
            k8s_provider, project_name, aws_region, cluster_name, karpenter_config, oidc_provider_id,
            cluster_endpoint=cluster_endpoint, cluster_ca=cluster_ca
        )

def _install_metrics_server(provider, project_name: str) -> None:
    """Install Metrics Server for Kubernetes metrics aggregation."""
    Chart(
        "metrics-server",
        ChartOpts(
            chart="metrics-server",
            version="3.8.2",
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/metrics-server",
            ),
            namespace="kube-system",
        ),
        opts=pulumi.ResourceOptions(provider=provider),
    )

def _install_karpenter(provider, project_name: str, aws_region: str, cluster_name: str, karpenter_config: dict, oidc_provider_id: str = None, cluster_endpoint=None, cluster_ca=None) -> None:
    """Install Karpenter for node autoscaling.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
        cluster_name: Name of the EKS cluster
        karpenter_config: Configuration for Karpenter
        oidc_provider_id: The OIDC provider ID for the EKS cluster
        cluster_endpoint: The endpoint URL for the EKS cluster
        cluster_ca: The base64-encoded CA certificate for the EKS cluster
    """
    import pulumi_aws as aws
    import pulumi_kubernetes as k8s
    import json
    
    # Create Karpenter namespace
    ns = k8s.core.v1.Namespace(
        "karpenter",
        metadata={"name": "karpenter"},
        opts=pulumi.ResourceOptions(provider=provider)
    )
    
    # Get AWS account ID
    account_id = aws.get_caller_identity().account_id
    
    # Create IAM policy for Karpenter
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:RunInstances", "ec2:CreateLaunchTemplate", "ec2:CreateFleet",
                    "ec2:TerminateInstances", "ec2:DescribeInstances", "ec2:DescribeInstanceTypes",
                    "ec2:DescribeLaunchTemplates", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups",
                    "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeSpotPriceHistory",
                    "pricing:GetProducts", "ssm:GetParameter", "iam:PassRole"
                ],
                "Resource": "*"
            }
        ]
    }
    
    # Create OIDC provider URL for the EKS cluster
    # Use pulumi.Output.concat to properly handle the OIDC provider URL
    oidc_provider_url = pulumi.Output.concat("oidc.eks.", aws_region, ".amazonaws.com/id/", oidc_provider_id)
    
    # Create the IAM role with the trust relationship policy
    role = aws.iam.Role(
        f"{project_name}-karpenter-role",
        assume_role_policy=pulumi.Output.all(account_id=account_id, oidc_url=oidc_provider_url).apply(
            lambda args: json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Federated": f"arn:aws:iam::{args['account_id']}:oidc-provider/{args['oidc_url']}"
                        },
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Condition": {
                            "StringEquals": {
                                f"{args['oidc_url']}:aud": "sts.amazonaws.com",
                                f"{args['oidc_url']}:sub": "system:serviceaccount:karpenter:karpenter"
                            }
                        }
                    }
                ]
            })
        ),
        tags={"Name": f"{project_name}-karpenter-role"}
    )
    
    # Create and attach required policies
    policy = aws.iam.Policy(
        f"{project_name}-karpenter-policy",
        description=f"Policy for Karpenter in {project_name}",
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:RunInstances", "ec2:CreateLaunchTemplate", "ec2:CreateFleet",
                        "ec2:TerminateInstances", "ec2:DescribeInstances", "ec2:DescribeInstanceTypes",
                        "ec2:DescribeLaunchTemplates", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups",
                        "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeSpotPriceHistory",
                        "pricing:GetProducts", "ssm:GetParameter", "iam:PassRole"
                    ],
                    "Resource": "*"
                }
            ]
        })
    )
    
    aws.iam.RolePolicyAttachment(
        f"{project_name}-karpenter-policy-attachment",
        role=role.name,
        policy_arn=policy.arn,
    )
    
    # Prepare Helm values
    helm_values = {
        "serviceAccount": {
            "create": True,
            "name": "karpenter",
            "annotations": {"eks.amazonaws.com/role-arn": role.arn}
        },
        "controller": {
            "clusterName": cluster_name,
            "clusterEndpoint": cluster_endpoint,
            "aws": {
                "defaultInstanceProfile": f"{project_name}-karpenter-instance-profile"
            },
            "replicas": karpenter_config.get("replicas", 2),
            "resources": {
                "limits": {"cpu": "1", "memory": "1Gi"},
                "requests": {"cpu": "1", "memory": "1Gi"}
            }
        },
        "logLevel": "debug"
    }
    
    # Add instance types if specified in config
    if "instanceTypes" in karpenter_config:
        helm_values["controller"]["aws"]["defaultInstanceTypes"] = karpenter_config["instanceTypes"]
    
    # Get version from config with a default fallback
    chart_version = karpenter_config.get('version', 'v0.15.0')
    
    # Install Karpenter using Helm
    karpenter_chart = Chart(
        "karpenter",
        ChartOpts(
            chart="karpenter",
            version=chart_version,
            fetch_opts=FetchOpts(repo="https://charts.karpenter.sh"),
            namespace="karpenter",
            values=helm_values
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[ns, role, policy],
            ignore_changes=["version"]
        )
    )
    
    # Export important values
    pulumi.export('karpenter_ready', True)
    pulumi.export('karpenter_role_arn', role.arn)
    
    return {
        "namespace": ns,
        "chart": karpenter_chart,
        "role": role,
        "policy": policy,
        "service_account": "karpenter"
    }

def _install_ebs_csi_driver(provider, project_name: str, aws_region: str) -> None:
    """Install AWS EBS CSI Driver for dynamic provisioning of EBS volumes.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
    """
    # Create the kube-system namespace if it doesn't exist
    ns = k8s.core.v1.Namespace.get(
        "kube-system",
        "kube-system",
        opts=pulumi.ResourceOptions(provider=provider),
    )
    
    # Get the ECR repository prefix based on the region
    ecr_prefix = f"{aws_region}.dkr.ecr.{aws_region}.amazonaws.com"
    
    # Install the AWS EBS CSI Driver
    Chart(
        "aws-ebs-csi-driver",
        ChartOpts(
            chart="aws-ebs-csi-driver",
            version="2.6.5",
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/aws-ebs-csi-driver",
            ),
            namespace=ns.metadata["name"],
            values={
                "region": aws_region,
                "controller": {
                    "image": {
                        "repository": f"{ecr_prefix}/eks/aws-ebs-csi-driver",
                        "tag": "v1.5.0"
                    },
                    "sidecars": {
                        "provisioner": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-provisioner",
                                "tag": "v2.2.1"
                            }
                        },
                        "attacher": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-attacher",
                                "tag": "v3.2.0"
                            }
                        },
                        "snapshotter": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-snapshotter",
                                "tag": "v4.2.0"
                            }
                        },
                        "resizer": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-resizer",
                                "tag": "v1.2.0"
                            }
                        },
                        "livenessProbe": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-livenessprobe",
                                "tag": "v2.3.0"
                            }
                        },
                        "nodeDriverRegistrar": {
                            "image": {
                                "repository": f"{ecr_prefix}/eks/csi-node-driver-registrar",
                                "tag": "v2.2.0"
                            }
                        }
                    },
                    "replicaCount": 2,
                    "serviceAccount": {
                        "create": True,
                        "name": "ebs-csi-controller-sa",
                        "annotations": {
                            "eks.amazonaws.com/role-arn": f"arn:aws:iam::${{pulumi.get_stack()}}:role/{project_name}-ebs-csi-controller-role"
                        },
                    },
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {
                                    "weight": 100,
                                    "podAffinityTerm": {
                                        "labelSelector": {
                                            "matchExpressions": [
                                                {
                                                    "key": "app",
                                                    "operator": "In",
                                                    "values": ["ebs-csi-controller"]
                                                }
                                            ]
                                        },
                                        "topologyKey": "kubernetes.io/hostname"
                                    }
                                }
                            ]
                        }
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "resources": {
                        "requests": {
                            "cpu": "200m",
                            "memory": "200Mi"
                        },
                        "limits": {
                            "cpu": "500m",
                            "memory": "500Mi"
                        }
                    }
                },
                "node": {
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "resources": {
                        "requests": {
                            "cpu": "50m",
                            "memory": "100Mi"
                        },
                        "limits": {
                            "cpu": "200m",
                            "memory": "200Mi"
                        }
                    }
                },
                "storageClasses": [
                    {
                        "name": "gp3",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "true"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "gp3",
                            "encrypted": "true"
                        }
                    },
                    {
                        "name": "gp3-encrypted",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "false"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "gp3",
                            "encrypted": "true"
                        }
                    },
                    {
                        "name": "sc1",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "false"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "sc1"
                        }
                    },
                    {
                        "name": "st1",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "false"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "st1"
                        }
                    },
                    {
                        "name": "io1",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "false"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "io1"
                        }
                    }
                ]
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[ns]),
    )
