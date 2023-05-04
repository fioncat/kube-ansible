import subprocess
import sys
import os
import yaml

from os.path import exists
from shutil import which

download_urls = {
    "etcd":
    "https://github.com/etcd-io/etcd/releases/download/v{0}/etcd-v{0}-linux-amd64.tar.gz",
    "containerd":
    "https://github.com/containerd/containerd/releases/download/v{0}/containerd-{0}-linux-amd64.tar.gz",
    "runc":
    "https://github.com/opencontainers/runc/releases/download/v{0}/runc.amd64",
    "crictl":
    "https://github.com/kubernetes-sigs/cri-tools/releases/download/v{0}/crictl-v{0}-linux-amd64.tar.gz",
    "cni":
    "https://github.com/containernetworking/plugins/releases/download/v{0}/cni-plugins-linux-amd64-v{0}.tgz",
    "kubeadm":
    "https://dl.k8s.io/release/v{0}/bin/linux/amd64/kubeadm",
    "kubelet":
    "https://dl.k8s.io/release/v{0}/bin/linux/amd64/kubelet",
    "kubectl":
    "https://dl.k8s.io/release/v{0}/bin/linux/amd64/kubectl",
    "calico":
    "https://raw.githubusercontent.com/projectcalico/calico/v{0}/manifests/tigera-operator.yaml",
}


def download(url, path):
    if which("wget") is not None:
        execute([
            "wget", "-q", "--show-progress",
            "--output-document={}".format(path), url
        ])
    elif which("curl") is not None:
        execute(["curl", "--fail", "--location", "--output", path, url])
    elif which("fetch") is not None:
        execute(["fetch", "--output={}".format(path), url])
    else:
        raise Exception("missing download tool, one of: wget, curl, fetch")


def execute(cmds):
    ret = subprocess.run(cmds)
    if not ret.returncode == 0:
        raise KeyboardInterrupt


def download_bin(name, version, suffix):
    path = f"bin/{name}_{version}{suffix}"
    if exists(path):
        return
    url = download_urls[name]
    url = url.format(version)

    if not exists("bin"):
        os.makedirs("bin")

    print(f"==> Downloading {name}...")
    download(url, path)


def main():
    if len(sys.argv) != 2:
        print("usage: download.py {inventory_name}")
        sys.exit(1)

    inventory = sys.argv[1]
    var_path = f"{inventory}/group_vars/all.yml"
    with open(var_path, "r") as file:
        data = yaml.safe_load(file)

    if 'etcd' in data:
        etcd = data['etcd']
        version = etcd['version']
        download_bin("etcd", version, ".tar.gz")

    if 'runtime' in data:
        runtime = data['runtime']
        version = runtime['version']
        download_bin("containerd", version, ".tar.gz")

        if 'runc' in runtime:
            version = runtime['runc']['version']
            download_bin("runc", version, "")

        if 'crictl' in runtime:
            version = runtime['crictl']['version']
            download_bin("crictl", version, ".tar.gz")

        if 'cni' in runtime:
            version = runtime['cni']['version']
            download_bin("cni", version, ".tar.gz")

    if 'cluster' in data:
        version = data['cluster']['version']
        download_bin("kubeadm", version, "")
        download_bin("kubelet", version, "")
        download_bin("kubectl", version, "")

    if 'calico' in data:
        if data['calico']['enable']:
            version = data['calico']['version']
            download_bin("calico", version, ".yaml")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(213)
    except Exception as e:
        print("error: {}".format(e))
        sys.exit(1)
