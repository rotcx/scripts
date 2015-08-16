#!/usr/bin/env python3
import os
import re
import sys
import io
from subprocess import call, Popen, check_output
import time

__author__ = 'ty'

from bs4 import BeautifulSoup
from bs4 import Tag

from cmfile import CMFile

import requests
import json


def sha1_file(file_path):
    import hashlib

    sha = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            block = f.read(2 ** 10)  # Magic number: one-megabyte blocks.
            if not block: break
            sha.update(block)
        return sha.hexdigest()


try:
    mode = sys.argv[1]
except IndexError:
    mode = "--download"

url = "http://download.cyanogenmod.org"

while True:

    cmFiles_dict = {}
    cmFiles = []
    count = 0

    download_dir = "/var/cyanogenmod/"

    if os.path.exists("cm.json"):
        with open('cm.json') as data_file:
            data = json.load(data_file)
            for d in data["cmFiles"]:
                cmFile = CMFile()
                cmFile.url = d["url"]
                cmFile.sha1 = d["sha1"]
                cmFiles.append(json.JSONDecoder().decode(cmFile.json()))
                count += 1

    r = requests.get(url, verify=False)

    # print(r.text)

    soup = BeautifulSoup(r.text)

    if mode and (mode == "--list" or mode == "-l"):
        td_list = soup.find_all('li', id=re.compile('device_.*'))

        print("codename".ljust(20) + "fullname")

        for td in td_list:
            for content in td.contents[0].contents:
                s = ""
                if isinstance(content, Tag):
                    device = content.text.rsplit(' ', 1)
                    s = device[1].replace('(', '').replace(')', '')
                    s = s.ljust(20) + device[0]
                    print(s)
    else:
        link_list = soup.find_all('a', href=re.compile('/get/jenkins/.*'))
        for link in link_list:
            if isinstance(link, Tag):

                cmFile = CMFile()
                cmFile.url = url + link.get('href')

                parent = link.parent
                if isinstance(parent, Tag):
                    sha1 = parent.find('small', class_='md5')
                    sha1 = sha1.text.splitlines()[1].strip().replace('sha1: ', '')
                    cmFile.sha1 = sha1
                    s = json.JSONDecoder().decode(cmFile.json())
                    if s in cmFiles:
                        print("downloaded, skip")
                    else:

                        while int(check_output('ps -ef | grep /root/bypy/bypy.py |grep -v grep |wc -l', shell=True)) > 5:
                            time.sleep(3)

                        # download zip and recovery.img and check hash
                        print(cmFile.url)

                        index = cmFile.url.rfind('/')
                        filename = cmFile.url[index + 1:]
                        print(filename)

                        device = ""
                        if filename.endswith('.img'):
                            device = filename.replace('-recovery.img', '')
                        else:
                            device = filename.replace('.zip', '')
                        device = device[device.rfind('-') + 1:]
                        print(device)

                        out_file = "{}{}/{}".format(download_dir, device, filename)

                        call("mkdir -p {}{}".format(download_dir, device), shell=True)

                        call("wget --progress=dot:binary \"{}\" -O \"{}\"".format(cmFile.url, out_file), shell=True)
                        if sha1_file(out_file) == cmFile.sha1:

                            # upload file via bypy

                            call("sha1sum {} > {}.sha1".format(out_file, out_file), shell=True)

                            cmFiles.append(s)
                            count += 1

                            if filename.endswith('.img'):
                                Popen("./cm.sh {}{}/{} {}".format(download_dir, device, filename, device), shell=True)
                            else:
                                Popen("./cm.sh {}{} {}".format(download_dir, device, device), shell=True)
                        else:
                            continue

    cmFiles_dict["count"] = count
    cmFiles_dict["cmFiles"] = cmFiles

    with io.open('cm.json', 'w') as f:
        json.dump(cmFiles_dict, f, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
