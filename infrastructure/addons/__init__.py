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
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts

def setup_addons(
    kubeconfig: pulumi.Output[str], 
    project_name: str, 
    aws_region: str,
    addons_config: dict,
    cluster_name: str,
    vpc_id: str,
    karpenter_config: dict = None
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
        _install_karpenter(k8s_provider, project_name, aws_region, cluster_name, karpenter_config)

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

def _install_ebs_csi_driver(provider, project_name: str, aws_region: str) -> None:
    """Install AWS EBS CSI Driver for EBS volume management."""
    Chart(
        "aws-ebs-csi-driver",
        ChartOpts(
            chart="aws-ebs-csi-driver",
            version="2.4.0",
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/aws-ebs-csi-driver",
            ),
            namespace="kube-system",
            values={
                "serviceAccount": {
                    "create": True,
                    "name": "ebs-csi-controller-sa",
                    "annotations": {
                        "eks.amazonaws.com/role-arn": f"arn:aws:iam::${{pulumi.get_stack()}}:role/{project_name}-ebs-csi-driver-role"
                    }
                },
                "controller": {
                    "replicaCount": 2,
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi"
                        },
                        "limits": {
                            "cpu": "500m",
                            "memory": "512Mi"
                        }
                    },
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {
                                    "weight": 100,
                                    "podAffinityTerm": {
                                        "labelSelector": {
                                            "matchExpressions": [
                                                {
                                                    "key": "app.kubernetes.io/name",
                                                    "operator": "In",
                                                    "values": ["aws-ebs-csi-driver"]
                                                }
                                            ]
                                        },
                                        "topologyKey": "kubernetes.io/hostname"
                                    }
                                }
                            ]
                        }
                    }
                },
                "node": {
                    "replicaCount": 2,
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi"
                        },
                        "limits": {
                            "cpu": "500m",
                            "memory": "512Mi"
                        }
                    },
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {
                                    "weight": 100,
                                    "podAffinityTerm": {
                                        "labelSelector": {
                                            "matchExpressions": [
                                                {
                                                    "key": "app.kubernetes.io/name",
                                                    "operator": "In",
                                                    "values": ["aws-ebs-csi-driver"]
                                                }
                                            ]
                                        },
                                        "topologyKey": "kubernetes.io/hostname"
                                    }
                                }
                            ]
                        }
                    }
                },
                "snapshotController": {
                    "replicaCount": 2,
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi"
                        },
                        "limits": {
                            "cpu": "500m",
                            "memory": "512Mi"
                        }
                    },
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {
                                    "weight": 100,
                                    "podAffinityTerm": {
                                        "labelSelector": {
                                            "matchExpressions": [
                                                {
                                                    "key": "app.kubernetes.io/name",
                                                    "operator": "In",
                                                    "values": ["aws-ebs-csi-driver"]
                                                }
                                            ]
                                        },
                                        "topologyKey": "kubernetes.io/hostname"
                                    }
                                }
                            ]
                        }
                    }
                },
                "cainjector": {
                    "replicaCount": 2,
                    "resources": {
                        "requests": {
                            "cpu": "100m",
                            "memory": "128Mi"
                        },
                        "limits": {
                            "cpu": "500m",
                            "memory": "512Mi"
                        }
                    },
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ],
                    "affinity": {
                        "podAntiAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                {
                                    "weight": 100,
                                    "podAffinityTerm": {
                                        "labelSelector": {
                                            "matchExpressions": [
                                                {
                                                    "key": "app.kubernetes.io/component",
                                                    "operator": "In",
                                                    "values": ["cainjector"]
                                                }
                                            ]
                                        },
                                        "topologyKey": "kubernetes.io/hostname"
                                    }
                                }
                            ]
                        }
                    }
                },
                "startupapicheck": {
                    "enabled": True,
                    "timeout": "5m",
                    "extraArgs": ["--enable-http01=false"],
                    "nodeSelector": {
                        "kubernetes.io/os": "linux"
                    },
                    "tolerations": [
                        {
                            "key": "CriticalAddonsOnly",
                            "operator": "Exists"
                        }
                    ]
                }
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[ns]),
    )

def _install_karpenter(provider, project_name: str, aws_region: str, cluster_name: str, karpenter_config: dict) -> None:
    """Install Karpenter for node autoscaling.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
        cluster_name: Name of the EKS cluster
        karpenter_config: Configuration for Karpenter
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
    
    # Create IAM policy for Karpenter
    policy_doc = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateLaunchTemplate",
                    "ec2:CreateFleet",
                    "ec2:CreateTags",
                    "ec2:DescribeLaunchTemplates",
                    "ec2:DescribeInstances",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeInstanceTypes",
                    "ec2:DescribeInstanceTypeOfferings",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DeleteLaunchTemplate",
                    "ec2:RunInstances",
                    "ssm:GetParameter",
                    "pricing:GetProducts",
                    "ec2:TerminateInstances"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": f"arn:aws:iam::*:role/{project_name}-karpenter-node-role"
            }
        ]
    })
    
    # Create IAM policy
    policy = aws.iam.Policy(
        f"{project_name}-karpenter-policy",
        policy=policy_doc,
        description="Policy for Karpenter to manage EC2 instances"
    )
    
    # Create IAM role for Karpenter controller
    assume_role_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Federated": f"arn:aws:iam::{pulumi.get_stack()}:oidc-provider/oidc.eks.{aws_region}.amazonaws.com/id/{provider.resource_name}"
                },
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"oidc.eks.{aws_region}.amazonaws.com/id/{provider.resource_name}:sub": "system:serviceaccount:karpenter:karpenter"
                    }
                }
            }
        ]
    })
    
    role = aws.iam.Role(
        f"{project_name}-karpenter-role",
        assume_role_policy=assume_role_policy,
        description="IAM role for Karpenter controller"
    )
    
    # Attach the policy to the role
    aws.iam.RolePolicyAttachment(
        f"{project_name}-karpenter-policy-attachment",
        role=role.name,
        policy_arn=policy.arn,
    )
    
    # Install Karpenter using Helm
    karpenter_chart = Chart(
        "karpenter",
        ChartOpts(
            chart="karpenter",
            version=karpenter_config.get("version", "v0.36.1"),
            fetch_opts=FetchOpts(
                repo="https://charts.karpenter.sh"
            ),
            namespace="karpenter",
            values={
                "serviceAccount": {
                    "create": True,
                    "name": "karpenter",
                    "annotations": {
                        "eks.amazonaws.com/role-arn": role.arn
                    }
                },
                "controller": {
                    "clusterName": cluster_name,
                    "clusterEndpoint": provider.cluster_endpoint,
                    "aws": {
                        "defaultInstanceProfile": f"{project_name}-karpenter-instance-profile",
                        "interruptionQueueName": f"{project_name}-karpenter-interruption-queue"
                    },
                    "replicas": karpenter_config.get("replicas", 2)
                },
                "webhook": {
                    "replicas": karpenter_config.get("replicas", 2)
                },
                "resources": {
                    "requests": {
                        "cpu": "1",
                        "memory": "1Gi"
                    },
                    "limits": {
                        "cpu": "1",
                        "memory": "1Gi"
                    }
                },
                "nodeSelector": {
                    "kubernetes.io/os": "linux"
                },
                "tolerations": [
                    {
                        "key": "CriticalAddonsOnly",
                        "operator": "Exists"
                    }
                ]
            }
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[ns, role, policy])
    )
    
    # Create default Karpenter Provisioner
    k8s.apiextensions.CustomResource(
        "karpenter-default-provisioner",
        api_version="karpenter.sh/v1alpha5",
        kind="Provisioner",
        metadata={
            "name": "default",
            "namespace": "karpenter"
        },
        spec={
            "requirements": [
                {
                    "key": "karpenter.sh/capacity-type",
                    "operator": "In",
                    "values": karpenter_config.get("capacityType", ["on-demand"])
                },
                {
                    "key": "kubernetes.io/arch",
                    "operator": "In",
                    "values": karpenter_config.get("architectures", ["amd64"])
                },
                {
                    "key": "karpenter.k8s.aws/instance-type",
                    "operator": "In",
                    "values": karpenter_config.get("instanceTypes", ["m5.large", "m5.xlarge", "m5.2xlarge"])
                }
            ],
            "limits": {
                "resources": {
                    "cpu": "1000",
                    "memory": "1000Gi"
                }
            },
            "providerRef": {
                "name": "default"
            },
            "consolidation": {
                "enabled": True
            },
            "ttlSecondsUntilExpired": karpenter_config.get("ttlSecondsUntilExpired", 2592000),  # 30 days
            "ttlSecondsAfterEmpty": karpenter_config.get("ttlSecondsAfterEmpty", 30)
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[karpenter_chart])
    )
    
    # Create AWSNodeTemplate
    k8s.apiextensions.CustomResource(
        "karpenter-awsnodetemplate",
        api_version="karpenter.k8s.aws/v1alpha1",
        kind="AWSNodeTemplate",
        metadata={
            "name": "default",
            "namespace": "karpenter"
        },
        spec={
            "subnetSelector": {
                "karpenter.sh/discovery": cluster_name
            },
            "securityGroupSelector": {
                "karpenter.sh/discovery": cluster_name
            },
            "tags": {
                "karpenter.sh/discovery": cluster_name,
                "karpenter.sh/managed-by": "karpenter"
            }
        },
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[karpenter_chart])
    )

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
