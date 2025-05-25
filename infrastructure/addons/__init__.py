"""
Kubernetes Add-ons Module

This module handles the installation and configuration of essential Kubernetes add-ons
for the EKS cluster, including:
- AWS Load Balancer Controller
- Cluster Autoscaler
- Metrics Server
- Kubernetes Dashboard
- External DNS
- Cert Manager
- AWS EBS CSI Driver
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
    vpc_id: str
) -> None:
    """
    Install and configure Kubernetes add-ons for the EKS cluster.
    
    Args:
        kubeconfig: Kubeconfig for the EKS cluster
        project_name: Name of the project for resource naming and tagging
        aws_region: AWS region where the cluster is deployed
        addons_config: Configuration for add-ons
    """
    # Create a Kubernetes provider instance
    k8s_provider = k8s.Provider(
        f"{project_name}-k8s-provider",
        kubeconfig=kubeconfig,
    )
    
    # Install Metrics Server (enabled by default)
    if addons_config.get("metricsServer", True):
        _install_metrics_server(k8s_provider, project_name)
    
    # Install Cluster Autoscaler if enabled
    if addons_config.get("clusterAutoscaler", True):
        _install_cluster_autoscaler(k8s_provider, project_name, aws_region, cluster_name)
    
    # Install AWS Load Balancer Controller if enabled
    if addons_config.get("awsLoadBalancerController", True):
        _install_aws_load_balancer_controller(k8s_provider, project_name, aws_region, cluster_name, vpc_id)
    
    # Install External DNS if enabled
    if addons_config.get("externalDns", True):
        _install_external_dns(k8s_provider, project_name, aws_region)
    
    # Install Cert Manager if enabled
    if addons_config.get("certManager", True):
        _install_cert_manager(k8s_provider, project_name)
    
    # Install AWS EBS CSI Driver if enabled
    if addons_config.get("ebsCsiDriver", True):
        _install_ebs_csi_driver(k8s_provider, project_name, aws_region)

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

def _install_cluster_autoscaler(provider, project_name: str, aws_region: str, cluster_name: str) -> None:
    """Install Cluster Autoscaler for automatic node scaling.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
    """
    # Get the cluster name from the provider's context
    # cluster_name is now passed as an argument
    
    # Create the Cluster Autoscaler deployment
    Chart(
        "cluster-autoscaler",
        ChartOpts(
            chart="cluster-autoscaler",
            version="9.10.7",
            fetch_opts=FetchOpts(
                repo="https://kubernetes.github.io/autoscaler",
            ),
            namespace="kube-system",
            values={
                "autoDiscovery": {
                    "clusterName": cluster_name,
                },
                "awsRegion": aws_region,
                "rbac": {"create": True},
                "serviceAccount": {
                    "create": True,
                    "name": "cluster-autoscaler",
                    "annotations": {
                        "eks.amazonaws.com/role-arn": f"arn:aws:iam::${{pulumi.get_stack()}}:role/{project_name}-cluster-autoscaler-role"
                    },
                },
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[provider]),
    )

def _install_aws_load_balancer_controller(provider, project_name: str, aws_region: str, cluster_name: str, vpc_id: str) -> None:
    """Install AWS Load Balancer Controller for managing AWS ALB/NLB.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
    """
    # Create IAM policy for the AWS Load Balancer Controller
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceLinkedRole",
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeInternetGateways",
                    "ec2:DescribeVpcs",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeInstances",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeTags",
                    "elasticloadbalancing:DescribeLoadBalancers",
                    "elasticloadbalancing:DescribeLoadBalancerAttributes",
                    "elasticloadbalancing:DescribeListeners",
                    "elasticloadbalancing:DescribeListenerCertificates",
                    "elasticloadbalancing:DescribeSSLPolicies",
                    "elasticloadbalancing:DescribeRules",
                    "elasticloadbalancing:DescribeTargetGroups",
                    "elasticloadbalancing:DescribeTargetGroupAttributes",
                    "elasticloadbalancing:DescribeTargetHealth",
                    "elasticloadbalancing:CreateLoadBalancer",
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:CreateRule",
                    "elasticloadbalancing:DeleteRule",
                    "elasticloadbalancing:SetWebAcl",
                    "elasticloadbalancing:ModifyListener",
                    "elasticloadbalancing:AddListenerCertificates",
                    "elasticloadbalancing:RemoveListenerCertificates",
                    "elasticloadbalancing:ModifyRule",
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:RemoveTags",
                    "elasticloadbalancing:DeleteLoadBalancer",
                    "elasticloadbalancing:ModifyLoadBalancerAttributes",
                    "elasticloadbalancing:AddTags",
                    "elasticloadbalancing:RemoveTags",
                    "elasticloadbalancing:RegisterTargets",
                    "elasticloadbalancing:DeregisterTargets",
                    "elasticloadbalancing:SetIpAddressType",
                    "elasticloadbalancing:SetSecurityGroups",
                    "elasticloadbalancing:SetSubnets",
                    "elasticloadbalancing:DeleteLoadBalancerListeners",
                    "elasticloadbalancing:ModifyTargetGroup",
                    "elasticloadbalancing:ModifyTargetGroupAttributes",
                    "elasticloadbalancing:DeleteTargetGroup",
                    "elasticloadbalancing:CreateTargetGroup",
                    "cognito-idp:DescribeUserPoolClient",
                    "acm:ListCertificates",
                    "acm:DescribeCertificate",
                    "iam:ListServerCertificates",
                    "iam:GetServerCertificate",
                    "waf-regional:GetWebACLForResource",
                    "waf-regional:GetWebACL",
                    "waf-regional:AssociateWebACL",
                    "waf-regional:DisassociateWebACL",
                    "wafv2:GetWebACL",
                    "wafv2:GetWebACLForResource",
                    "wafv2:AssociateWebACL",
                    "wafv2:DisassociateWebACL",
                    "shield:GetSubscriptionState",
                    "shield:DescribeProtection",
                    "shield:CreateProtection",
                    "shield:DeleteProtection",
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags",
                    "ec2:DeleteTags"
                ],
                "Resource": "arn:aws:ec2:*:*:security-group/*",
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": "CreateSecurityGroup"
                    },
                    "Null": {
                        "aws:RequestedTag/elbv2.k8s.aws/cluster": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags",
                    "ec2:DeleteTags"
                ],
                "Resource": "arn:aws:ec2:*:*:security-group/*",
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": [
                            "CreateSecurityGroup",
                            "AuthorizeSecurityGroupIngress",
                            "AuthorizeSecurityGroupEgress",
                            "RevokeSecurityGroupIngress",
                            "RevokeSecurityGroupEgress"
                        ]
                    },
                    "Null": {
                        "aws:RequestedTag/elbv2.k8s.aws/resource": "false",
                        "aws:ResourceTag/elbv2.k8s.aws/resource": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:DeleteSecurityGroup"
                ],
                "Resource": "*",
                "Condition": {
                    "Null": {
                        "aws:ResourceTag/elbv2.k8s.aws/resource": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:CreateListener",
                    "elasticloadbalancing:DeleteListener",
                    "elasticloadbalancing:CreateRule",
                    "elasticloadbalancing:DeleteRule"
                ],
                "Resource": [
                    "arn:aws:elasticloadbalancing:*:*:listener/net/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener/app/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener-rule/net/*/*/*",
                    "arn:aws:elasticloadbalancing:*:*:listener-rule/app/*/*/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateServiceLinkedRole"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "iam:AWSServiceName": "elasticloadbalancing.amazonaws.com"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags"
                ],
                "Resource": [
                    "arn:aws:ec2:*:*:security-group/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": "CreateSecurityGroup"
                    },
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/resource": "false"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags"
                ],
                "Resource": [
                    "arn:aws:ec2:*:*:security-group/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": "CreateSecurityGroup"
                    },
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/resource": "true"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateSecurityGroup"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags"
                ],
                "Resource": [
                    "arn:aws:ec2:*:*:security-group/*"
                ],
                "Condition": {
                    "StringEquals": {
                        "ec2:CreateAction": "CreateSecurityGroup"
                    },
                    "Null": {
                        "aws:RequestTag/elbv2.k8s.aws/resource": "false"
                    }
                }
            }
        ]
    }
    
    # Install AWS Load Balancer Controller
    Chart(
        "aws-load-balancer-controller",
        ChartOpts(
            chart="aws-load-balancer-controller",
            version="1.4.1",
            fetch_opts=FetchOpts(
                repo="https://aws.github.io/eks-charts",
            ),
            namespace="kube-system",
            values={
                "clusterName": cluster_name,
                "vpcId": vpc_id,
                "serviceAccount": {
                    "create": True,
                    "name": "aws-load-balancer-controller",
                    "annotations": {
                        "eks.amazonaws.com/role-arn": f"arn:aws:iam::${{pulumi.get_stack()}}:role/{project_name}-aws-load-balancer-controller-role"
                    },
                },
                "region": aws_region,
                "image": {
                    "repository": f"{aws_region}.dkr.ecr.{aws_region}.amazonaws.com/amazon/aws-load-balancer-controller",
                    "tag": "v2.4.2",
                },
                "replicaCount": 2,
                "resources": {
                    "requests": {
                        "cpu": "0.5",
                        "memory": "512Mi"
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
                ],
                "affinity": {
                    "podAntiAffinity": {
                        "requiredDuringSchedulingIgnoredDuringExecution": [
                            {
                                "labelSelector": {
                                    "matchExpressions": [
                                        {
                                            "key": "app.kubernetes.io/name",
                                            "operator": "In",
                                            "values": ["aws-load-balancer-controller"]
                                        }
                                    ]
                                },
                                "topologyKey": "kubernetes.io/hostname"
                            }
                        ]
                    }
                }
            },
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[provider]),
    )

def _install_external_dns(provider, project_name: str, aws_region: str) -> None:
    """Install External DNS for managing DNS records in Route 53.
    
    Args:
        provider: The Kubernetes provider
        project_name: Name of the project for resource naming
        aws_region: AWS region where the cluster is deployed
    """
    Chart(
        "external-dns",
        ChartOpts(
            chart="external-dns",
            version="5.4.6",
            fetch_opts=FetchOpts(
                repo="https://kubernetes-sigs.github.io/external-dns",
            ),
            namespace="kube-system",
            values={
                "serviceAccount": {
                    "create": True,
                    "name": "external-dns",
                    "annotations": {
                        "eks.amazonaws.com/role-arn": f"arn:aws:iam::${{pulumi.get_stack()}}:role/{project_name}-external-dns-role"
                    },
                },
                "provider": "aws",
                "policy": "sync",
                "aws": {
                    "region": aws_region,
                    "zoneType": "public",
                },
                "sources": ["service", "ingress"],
                "logLevel": "info",
                "logFormat": "json",
                "interval": "1m",
                "triggerLoopOnEvent": True,
                "replicas": 2,
                "resources": {
                    "limits": {
                        "cpu": "100m",
                        "memory": "256Mi"
                    },
                    "requests": {
                        "cpu": "50m",
                        "memory": "128Mi"
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
                                                "values": ["external-dns"]
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
        ),
        opts=pulumi.ResourceOptions(provider=provider, depends_on=[provider]),
    )

def _install_cert_manager(provider, project_name: str) -> None:
    """Install Cert Manager for managing TLS certificates."""
    # Create the cert-manager namespace
    ns = k8s.core.v1.Namespace(
        "cert-manager",
        metadata={"name": "cert-manager"},
        opts=pulumi.ResourceOptions(provider=provider),
    )
    
    # Install cert-manager
    Chart(
        "cert-manager",
        ChartOpts(
            chart="cert-manager",
            version="v1.7.1",
            fetch_opts=FetchOpts(
                repo="https://charts.jetstack.io",
            ),
            namespace=ns.metadata["name"],
            values={
                "installCRDs": True,
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
                                                "values": ["cert-manager"]
                                            }
                                        ]
                                    },
                                    "topologyKey": "kubernetes.io/hostname"
                                }
                            }
                        ]
                    }
                },
                "webhook": {
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
                                                    "values": ["webhook"]
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
                        "name": "gp2",
                        "annotations": {
                            "storageclass.kubernetes.io/is-default-class": "false"
                        },
                        "volumeBindingMode": "WaitForFirstConsumer",
                        "reclaimPolicy": "Delete",
                        "parameters": {
                            "type": "gp2"
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
