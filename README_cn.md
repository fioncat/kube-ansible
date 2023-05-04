# kube-ansible

kube-ansible是一个用于快速部署高可用Kubernetes集群的`ansible playbook`。它适用于对Kubernetes较为熟悉的用户使用，能方便地拉起一个生产可用的集群。

它有如下特点：

- 基于`kubeadm`。
- 手动生成证书，可以深度配置`openssl`细节，不再受到`kubeadm`自动生成证书只有1年有效期的烦恼。
- 高度定制化，支持配置集群版本、网络、镜像仓库等细节。
- `etcd`可以独立部署或集成到`control-plane`中。
- 高可用架构，集群应该由至少3台`control-plane`节点和若干`worker`节点组成。
- （可选）基于`keepalived`实现`apiserver`负载均衡，简单高效，无需再额外部署负载均衡器。
- （可选）可以部署`calico`网络插件，实现`overlay`或`underlay`网络。

结合了`ansible`和`kubeadm`而超能力，你会发现部署Kubernetes集群变得如此简单！

## 准备机器

建议至少准备3台机器用于部署集群的`control-plane`，若干机器用于部署`worker`。

对机器有如下要求：

- 操作系统必须是Linux，发行版目前支持`CentOS`和`Ubuntu`。
- 机器配置不建议低于`2C 4GiB`，否则一些Kubernetes组件运行可能会有问题。
- 机器之间网络打通，不需要NAT做转换。
- 正确地配置了软件包源，能够使用`yum`或`apt`等包管理器下载依赖。
- 防火墙得到了正确的配置，一些Kubernetes的常见端口应该放开。

这里假设我们有下面4台机器：

- 10.0.0.1: 第一台`control-plane`节点。同时用作`kubeadm init`初始化集群的节点。
- 10.0.0.2: 第二台`control-plane`节点。
- 10.0.0.3: 第三台`control-plane`节点。
- 10.0.0.4: `worker`节点。

`etcd`将会被集成到3台`control-plane`节点中。

编辑[inventory/all](inventory/all)，将上面的节点加入。注意第一个`control-plane`节点用于初始化集群，它需要被单独配置到`init`组里面，而不在`master`组：

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

如果你执行`ansible`的机器无法访问内网，需要通过外网IP进行登录，可以通过`node`来配置内网IP：

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

上面的例子中，`106.74.0.*`是外网IP，用于提供给`ansible`远程登录节点使用。`10.0.0.*`是内网IP，用于集群内部访问用。


## 配置集群

编辑[inventory/group_vars/all.yml](inventory/group_vars/all.yml)文件，对集群进行配置：

```yaml
etcd:
  version: "3.4.25"
  # ETCD ssl证书的过期时间
  cert_expire_days: 3650

  # 需要添加给ssl证书的额外DNS和IP。如果你有额外的外部负载均衡器，请配置在这里。
  extra_cert_dns: []
  extra_cert_ip: []

runtime:
  version: "1.6.20"
  # containerd的socket文件地址，必须是绝对路径。
  socket: "/run/containerd/containerd.sock"
  runc:
    version: "1.1.7"
  crictl:
    version: "1.27.0"
  cni:
    enable: true
    version: "1.2.0"

apiserver:
  # APIServer 的访问地址，一般是一个负载均衡器地址。如果使用了keepalived，这里将会
  # 作为一个VIP存在。只能在节点内访问。
  endpoint: "6.0.0.6"

  # 是否开启keepalived，如果你的control-plane数量固定，强烈建议开启。
  # 如果未来有增加control-plane的需求，建议关闭并使用独立的负载均衡器。
  # 注意一旦开启，endpoint将会变成VIP，只能在集群节点内使用。如果需要外部访问APIServer
  # 请安装独立的负载均衡器。
  keepalived: true

  # 用户Pod访问APIServer的ClusterIP，一般是Service CIDR的第一个IP。
  cluster_ip: "192.1.0.1"

  # APIServer的额外启动参数
  extra_args: {}

  # APIServer ssl证书的过期时间
  cert_expire_days: 3650

  # 需要添加给ssl证书的额外DNS和IP。如果你有额外的外部负载均衡器，请配置在这里。
  extra_cert_dns: []
  extra_cert_ip: []

cluster:
  # Kubernetes集群版本，kubelet, kubeadm, kubectl以及所有控制及组件都会保持一致。
  version: "1.24.13"

  # 用于kubeadm join的bootstrap token，有格式要求，见：https://kubernetes.io/docs/reference/access-authn-authz/bootstrap-tokens/
  # 该token每隔24小时会过期，在执行`add-worker` playbook的时候会自动探测并refresh。
  bootstrap_token: "9a08jv.c0izixklcxtmnze7"

  name: "my-cluster"
  domain: "cluster.local"

  # Service CIDR，不要跟节点网络或Pod网络有重叠。
  service_cidr: "192.1.0.0/16"
  # Pod CIDR，一些网络插件（例如calico）会使用此配置。
  pod_cidr: "192.168.0.0/16"

  # 镜像仓库，kubeadm会从这里拉取控制组件镜像。
  image_registry: "registry.cn-hangzhou.aliyuncs.com/google_containers"
  # pause镜像，所有Pod都会先使用这个镜像。
  sandbox_image: "registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.7"

calico:
  # 是否开启calico网络插件，强烈建议开启，否则只能使用kubenet，Pod可能无法跨节点访问。
  # 有关calico，见：https://docs.tigera.io/calico/latest/about/
  enable: true
  version: "3.25.1"

  encapsulation: "VXLANCrossSubnet"
  operator_image: "quay.io/tigera/operator"
  image_registry: ""
```

配置好之后，需要先下载部署集群所用到的所有二进制文件，我们提供了[download.py](download.py)脚本帮助你一键下载，执行：

```bash
python3 download.py inventory
```

所有二进制都会被下载到`./bin`下面，它们在部署的时候会被`ansible`上传到服务器中。

## 生成证书

在开始部署之前，需要生成集群用到的所有ssl证书文件，证书生成是在本地进行的，请确保你的机器已经正确安装了`openssl`工具。

生成证书：

```bash
ansible-playbook -i inventory gencert.yml
```

证书会被生成到`./pki/{cluster_name}`下面，包括Kubernetes和etcd的证书。

## 部署集群

现在，可以开始部署集群了，执行：

```bash
ansible-playbook -i inventory site.yml
```

部署速度取决于你的网络，对于3台`control-plane`加一台`worker`的规模来说，`3M`的带宽一般需要10分钟左右。

## 验证

部署结束之后，登录任一一台`control-plane`，就可以使用`kubectl`命令验证集群是否正确部署完成：

```bash
$ kubectl get node
NAME       STATUS   ROLES           AGE   VERSION
10.0.0.4   Ready    <none>          55m   v1.24.13
10.0.0.1   Ready    control-plane   57m   v1.24.13
10.0.0.2   Ready    control-plane   55m   v1.24.13
10.0.0.3   Ready    control-plane   55m   v1.24.13
```

> 注意，ansible执行完毕之后几分钟内节点可能还是NotReady的状态，这是正常现象，因为calico需要一定时间来初始化。

可以观察控制组件、coredns、calico是否正确部署：

```bash
kubectl get po -A
```

## 添加工作节点

如果在一段时间之后，需要增加新的工作节点，可以编辑`inventory/all`，在`toadd`组加上新的节点：

```config
[toadd]
10.0.0.5
```

增加完成之后，执行：

```bash
ansible-playbook -i inventory add-node.yml
```
