# kube-ansible

kube-ansible is an Ansible playbook used for quickly creating a high-availability Kubernetes cluster. It is suitable for users who are familiar with Kubernetes.

For a high-availability Kubernetes cluster, the following requirements need to be met:

- Three or more master nodes to deploy control-plane components. Non-control Pods cannot be scheduled.
- A high-availability etcd cluster, which can be deployed on the master or independently. It is recommended to have more than three nodes and the number of nodes should be odd.
- Several worker nodes.

kube-ansible is used to help you create such a cluster, with the following features:

- Use `openssl` to generate SSL certificates, allowing you to freely specify certificate expiration time and other parameters, without worrying about `kubeadm` generated certificates being valid for only one year. Automatic distribution of certificates is supported.
- Provide download script to download corresponding versions of binary files, including etcd, kubelet, kubectl, and kubeadm, based on the configuration.
- Cluster parameters can be dynamically configured through `ansible group vars`, including cidr and image registry.
- Supports deploying etcd on the master nodes or on separate nodes.
- Container runtime uses `containerd`.
- Use `kubeadm init` to initialize the cluster, and then use `kubeadm join` to add nodes to the cluster one by one.
- After initializing the cluster, `calico` network plug-in can be deployed.
- After the cluster is deployed, new worker nodes can be added to the cluster through the `add-node playbook`.
