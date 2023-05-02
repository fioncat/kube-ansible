import subprocess
import json
import os
import sys

from os.path import exists
from shutil import which


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


def info(msg):
    print("==> {}".format(msg))


def read_versions():
    with open("versions.json", "r") as file:
        data = json.load(file)
        return data


def skip_download(dir, name):
    if not exists(dir):
        os.makedirs(dir)
    path = "{}/{}".format(dir, name)
    if exists(path):
        info("{} already exists, skip".format(name))
        return True
    return False


def get_version(data, name):
    if name not in data:
        raise Exception("could not find version for {}".format(name))
    ver = data[name]
    if not ver:
        raise Exception("version for {} is empty".format(name))
    return ver


def download_etcd(data):
    if skip_download("binary/etcd", "etcd"):
        return
    ver = get_version(data, "etcd")
    url = f"https://github.com/etcd-io/etcd/releases/download/v{ver}/etcd-v{ver}-linux-amd64.tar.gz"

    info("Downloading etcd...")
    download(url, "binary/etcd/etcd.tar.gz")

    info("Unzipping etcd..")
    execute(["tar", "xzf", "binary/etcd/etcd.tar.gz", "-C", "binary/etcd"])

    out_dir = f"binary/etcd/etcd-v{ver}-linux-amd64"

    execute(["mv", f"{out_dir}/etcd", "binary/etcd/etcd"])
    execute(["mv", f"{out_dir}/etcdctl", "binary/etcd/etcdctl"])

    execute(["rm", "binary/etcd/etcd.tar.gz"])
    execute(["rm", "-rf", out_dir])


def download_runtime(data):
    runtime = get_version(data, "runtime")
    if not skip_download("binary/runtime", "runc"):
        ver = get_version(runtime, "runc")
        url = f"https://github.com/opencontainers/runc/releases/download/v{ver}/runc.amd64"
        info("Downloading runc...")
        download(url, "binary/runtime/runc")

    if not skip_download("binary/runtime", "containerd"):
        ver = get_version(runtime, "containerd")
        url = f"https://github.com/containerd/containerd/releases/download/v{ver}/containerd-{ver}-linux-amd64.tar.gz"
        info("Downloading containerd...")
        download(url, "binary/runtime/containerd.tar.gz")
        info("Unzipping containerd...")
        execute([
            "tar", "xzf", "binary/runtime/containerd.tar.gz", "-C",
            "binary/runtime"
        ])
        execute(["mv", "binary/runtime/bin", "binary/runtime/containerd"])
        execute(["rm", "binary/runtime/containerd.tar.gz"])

    if not skip_download("binary/runtime", "crictl"):
        ver = get_version(runtime, "crictl")
        url = f"https://github.com/kubernetes-sigs/cri-tools/releases/download/v{ver}/crictl-v{ver}-linux-amd64.tar.gz"
        info("Downloading critl...")
        download(url, "binary/runtime/crictl.tar.gz")
        execute([
            "tar", "xzf", "binary/runtime/crictl.tar.gz", "-C",
            "binary/runtime"
        ])
        info("Unzipping crictl...")
        execute(["rm", "binary/runtime/crictl.tar.gz"])


def download_kubernetes(data):
    ver = get_version(data, "kubernetes")
    if not skip_download("binary/kubernetes", "kubeadm"):
        url = f"https://dl.k8s.io/release/v{ver}/bin/linux/amd64/kubeadm"
        info("Downloading kubeadm...")
        download(url, "binary/kubernetes/kubeadm")

    if not skip_download("binary/kubernetes", "kubelet"):
        url = f"https://dl.k8s.io/release/v{ver}/bin/linux/amd64/kubelet"
        info("Downloading kubelet...")
        download(url, "binary/kubernetes/kubelet")

    if not skip_download("binary/kubernetes", "kubectl"):
        url = f"https://dl.k8s.io/release/v{ver}/bin/linux/amd64/kubectl"
        info("Downloading kubectl...")
        download(url, "binary/kubernetes/kubectl")


def download_cni(data):
    if skip_download("binary/cni", "cni.tar.gz"):
        return
    ver = get_version(data, "cni")
    url = f"https://github.com/containernetworking/plugins/releases/download/v{ver}/cni-plugins-linux-amd64-v{ver}.tgz"
    info("Downloading cni...")
    download(url, "binary/cni/cni.tar.gz")


def download_calico(data):
    ver = get_version(data, "calico")
    if skip_download("binary/calico", "tigera-operator.yaml"):
        return
    url = f"https://raw.githubusercontent.com/projectcalico/calico/v{ver}/manifests/tigera-operator.yaml"
    info("Downloading calico...")
    download(url, "binary/calico/tigera-operator.yaml")
    with open("binary/calico/tigera-operator.yaml", 'r+') as file:
        data = file.read()
        data = data.replace("quay.io/tigera/operator",
                            '{{ calico_operator_image }}')
    with open("binary/calico/tigera-operator.yaml", 'w+') as file:
        file.write(data)


def main():
    info("parse versions")
    data = read_versions()

    info("handle etcd")
    download_etcd(data)

    info("handle runtime")
    download_runtime(data)

    info("handle kubernetes")
    download_kubernetes(data)

    info("handle cni")
    download_cni(data)

    info("handle calico")
    download_calico(data)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(213)
    except Exception as e:
        print("error: {}".format(e))
        sys.exit(1)
