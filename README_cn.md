# kube-ansible

kube-ansible是一个用来快速创建高可用kubernetes集群的ansble playbook。它适用于对kubernetes较为熟悉的用户。

对于一个高可用kubernetes集群，我们有以下要求：

- 3台或更多master节点，部署control-plane组件。非控制Pod无法调度上来。
- 一个高可用etcd集群，可以部署在master上或独立部署。建议大于3个节点并且节点数为奇数。
- 若干worker节点。

kube-ansible用来帮助你创建这样一个集群，它有如下特点：

- 使用`openssl`生成ssl证书，可以自由指定证书过期时间等参数，不再因为`kubeadm`生成证书只有一年有效期而头疼。支持自动分发证书。
- 提供下载脚本，根据配置下载对应版本的二进制文件，包括etcd、kubelet、kubectl、kubeadm等。
- 可以通过`ansible group vars`来动态配置集群参数，包括cidr、image registry等。
- 支持将etcd部署在master节点或者在独立的节点上面。
- 容器运行时使用`containerd`。
- 使用`kubeadm init`初始化集群，然后使用`kubeadm join`来将节点逐一加入集群。
- 初始化集群后支持部署`calico`网络插件。
- 集群部署完成之后，可以通过`add-node playbook`将新的工作节点加入集群。
