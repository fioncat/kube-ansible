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
    url = f"https://github.com/etcd-io/etcd/releases/download/{ver}/etcd-{ver}-linux-amd64.tar.gz"

    info("Downloading etcd...")
    download(url, "binary/etcd/etcd.tar.gz")

    info("Unzip etcd..")
    execute(["tar", "xzf", "binary/etcd/etcd.tar.gz", "-C", "binary/etcd"])

    out_dir = f"binary/etcd/etcd-{ver}-linux-amd64"

    execute(["mv", f"{out_dir}/etcd", "binary/etcd/etcd"])
    execute(["mv", f"{out_dir}/etcdctl", "binary/etcd/etcdctl"])

    execute(["rm", "binary/etcd/etcd.tar.gz"])
    execute(["rm", "-rf", out_dir])


def main():
    info("begin to handle etcd")
    data = read_versions()
    download_etcd(data)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(213)
    except Exception as e:
        print("error: {}".format(e))
        sys.exit(1)
