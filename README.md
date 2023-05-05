# kube-ansible

kube-ansible is an `ansible playbook` used for quickly deploying a highly available Kubernetes cluster. It is designed for users familiar with Kubernetes and allows for the easy launch of a production-ready cluster.

It features the following:

- Based on `kubeadm`.
- Manually generated certificates, allowing for deep configuration of `openssl` details and eliminating the hassle of `kubeadm`-generated certificates with only a one-year validity period.
- Highly customizable, supporting configuration of cluster versions, networking, image repositories, and other details.
- `etcd` can be deployed independently or integrated into the `control-plane`.
- Highly available architecture, with the cluster consisting of at least three `control-plane` nodes and several `worker` nodes.
- (Optional) `apiserver` load balancing based on `keepalived`, simple and efficient, eliminating the need for additional load balancers.
- (Optional) `calico` network plugin can be deployed to achieve `overlay` or `underlay` networking.

With the combined power of `ansible` and `kubeadm`, you will find that deploying a Kubernetes cluster has become so simple!

## Prepare machines

It is recommended to prepare at least 3 machines for deploying the Kubernetes cluster as `control-plane` nodes and several machines for deploying `worker` nodes.

The machines must meet the following requirements:

- The operating system must be `Linux` with architecture `amd64`. Currently recommended distributions are `CentOS` and `Ubuntu`.
- The machine specification should not be less than `2C 4GiB`, otherwise, some Kubernetes components may have problems running.
- The networks between machines must be interconnected without NAT.
- The software package source is correctly configured, and dependencies can be downloaded using package managers such as `yum` or `apt`.

Here, let's assume that we have the following 4 machines:

- 10.0.0.1: The first `control-plane` node, which is also used to initialize the cluster with `kubeadm init`.
- 10.0.0.2: The second `control-plane` node.
- 10.0.0.3: The third `control-plane` node.
- 10.0.0.4: The `worker` node.

`etcd` will be integrated into the 3 `control-plane` nodes.

In addition, you will need a machine to execute the Ansible Playbook. It should be able to access the cluster machines and have SSH key-based authentication configured.

Edit [inventory/all](inventory/all) and add the above nodes. Note that the first `control-plane` node is used to initialize the cluster and should be configured in the `init` group separately, instead of in the `master` group:

```config
[etcd]
10.0.0.1
10.0.0.2
10.0.0.3

[init]
10.0.0.1

[master]
10.0.0.2
10.0.0.3

[worker]
10.0.0.4
```

If the machine that executes Ansible cannot access the intranet and needs to login through the external IP, you can configure the intranet IP through `node`:

```config
[etcd]
106.75.0.1
106.75.0.2
106.75.0.3

[init]
106.75.0.1 node=10.0.0.1

[master]
106.75.0.2 node=10.0.0.2
106.75.0.3 node=10.0.0.3

[worker]
106.75.0.4 node=10.0.0.4
```

In the example above, `106.74.0.*` is the external IP used for Ansible remote login to the nodes, and `10.0.0.*` is the intranet IP used for internal access within the cluster.

## Cluster Configuration

Edit the [inventory/group_vars/all.yml](inventory/group_vars/all.yml) file to configure the cluster:

```yaml
etcd:
  version: "3.4.25"
  # Expiration time of the ETCD SSL certificate
  cert_expire_days: 3650

  # Additional DNS and IP addresses to add to the SSL certificate. If you have
  # additional external load balancers, configure them here.
  extra_cert_dns: []
  extra_cert_ip: []

runtime:
  version: "1.6.20"
  # The socket file address of containerd, must be an absolute path.
  socket: "/run/containerd/containerd.sock"
  runc:
    version: "1.1.7"
  crictl:
    version: "1.27.0"
  cni:
    enable: true
    version: "1.2.0"

apiserver:
  # For accessing the API server within the cluster, usually a load balancer address or DNS.
  # If Keepalived is enabled, it will be used as a keepalived VIP.
  endpoint: "6.0.0.6"

  # Whether to enable keepalived. If the number of control-planes is fixed, it
  # is strongly recommended to enable it.
  # If there is a future need to increase the number of control-planes, it is
  # recommended to disable it and use an independent load balancer instead.
  # Note that once enabled, the endpoint will become a VIP and can only be used
  # within the cluster nodes. If external access to the APIServer is required,
  # please install an independent load balancer.
  keepalived: true

  # The ClusterIP that user Pods use to access the APIServer, generally the first
  # IP of the Service CIDR.
  cluster_ip: "192.1.0.1"

  # Additional startup parameters for APIServer
  extra_args: {}

  # Expiration time of the APIServer SSL certificate
  cert_expire_days: 3650

  # Additional DNS and IP addresses to add to the SSL certificate. If you have
  # additional external load balancers, configure them here.
  extra_cert_dns: []
  extra_cert_ip: []

cluster:
  # Kubernetes cluster version. kubelet, kubeadm, kubectl, and all control
  # components will remain consistent.
  version: "1.24.13"

  # The bootstrap token used for kubeadm join has formatting requirements,
  # This token will expire every 24 hours and will be automatically detected and
  # refreshed when executing the `add-worker` playbook.
  # See: https://kubernetes.io/docs/reference/access-authn-authz/bootstrap-tokens/
  bootstrap_token: "9a08jv.c0izixklcxtmnze7"

  name: "my-cluster"
  domain: "cluster.local"

  # Service CIDR, do not overlap with node network or Pod network.
  service_cidr: "192.1.0.0/16"
  # Pod CIDR, some network plugins (such as Calico) will use this configuration.
  pod_cidr: "192.168.0.0/16"

  # Image registry, kubeadm will pull control component images from here.
  image_registry: "registry.cn-hangzhou.aliyuncs.com/google_containers"
  # The pause image, which will be used by all Pods first.
  sandbox_image: "registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.7"

calico:
  # Whether to enable the Calico network plugin. It is strongly recommended to
  # enable it, otherwise only kubenet can be used and Pods may not be able to
  # access across nodes.
  # See: https://docs.tigera.io/calico/latest/about/
  enable: true
  version: "3.25.1"

  encapsulation: "VXLANCrossSubnet"
  operator_image: "quay.io/tigera/operator"
  image_registry: ""

```

After configuration, you need to download all the binary files required for deploying the cluster. We provide a script called [download.py](download.py) to help you download them with one click. Run the following command:

```bash
python3 download.py inventory
```

All the binaries will be downloaded to `./bin` directory, and they will be uploaded to the servers by Ansible during deployment.

## Generating Certificates

Before starting the deployment, you need to generate all the SSL certificate files required by the cluster. The certificate generation is done locally, so please make sure that your Ansible machine has `openssl` tool installed correctly.

To generate the certificates, run the following command:

```bash
ansible-playbook -i inventory gencert.yml
```

The certificates will be generated in `./pki/{cluster_name}` directory, including the certificates for Kubernetes and etcd.

## Deploying the Cluster

Now, you can start deploying the cluster by running the following command:

```bash
ansible-playbook -i inventory site.yml
```

The deployment speed depends on your network. For a cluster with 3 `control-plane` nodes and 1 `worker` node, it usually takes about 10 minutes with a bandwidth of 3M.

## Verification

After the deployment is completed, you can login to any `control-plane` node and use `kubectl` command to verify if the cluster is deployed correctly:

```bash
$ kubectl get node
NAME       STATUS   ROLES           AGE   VERSION
10.0.0.4   Ready    <none>          55m   v1.24.13
10.0.0.1   Ready    control-plane   57m   v1.24.13
10.0.0.2   Ready    control-plane   55m   v1.24.13
10.0.0.3   Ready    control-plane   55m   v1.24.13
```

> Note that the nodes may still be in `NotReady` status within a few minutes after the completion of Ansible execution, which is normal because Calico needs some time to initialize.
> You can use `kubectl describe node` to check if Kubelet is not ready due to `cni plugin not initialized`.

You can observe if the control components are deployed correctly by running:

```bash
kubectl -n kube-system get po
```

`kubeadm` will deploy all control components as Pod in `kube-system` namespace.

## Adding Worker Nodes

If you need to add new worker nodes after some time, you can edit `inventory/all` and add the new nodes to the `toadd` group:

```config
[toadd]
10.0.0.5
```

After adding the nodes, run the following command:

```bash
ansible-playbook -i inventory add-node.yml
```

This will add the new worker nodes to the cluster.
