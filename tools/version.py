#!/usr/bin/python

import argparse
import re
import sys
import subprocess
from pathlib import Path


VERSION_PATH = Path(r"../VERSION")
VERSION_FORMAT = re.compile("^\d+[.]\d+[.]?\d*$")

parser = argparse.ArgumentParser(prog="version.py", description="Increase version number in source code and git repository")
parser.add_argument("new_version", nargs="?", default=None, help="The new version number. If no version number is provided, the default is to increase the patch number by one")
args = parser.parse_args()
new_version = args.new_version

try:
    with open(VERSION_PATH, "r") as v:
        old_version : str = v.readline().strip()
except FileNotFoundError:
    print(f"File '{VERSION_PATH}' not found")
    sys.exit()

if not VERSION_FORMAT.match(old_version):
    print(f"Version string {old_version} in {VERSION_PATH} does not match required format {VERSION_FORMAT.pattern}")
    sys.exit()

if new_version is not None and not VERSION_FORMAT.match(new_version):
    print(f"New version string '{new_version}' does not match required pattern '{VERSION_FORMAT.pattern}'.")
    sys.exit()

if not new_version:
   split = old_version.split(".")
   major : str = split[0]
   minor : str = split[1]
   patch : int = int(split[2]) if len(split) > 2 else 0
   patch = patch + 1  # Auto-increment when no other version specified
   new_version = f"{major}.{minor}.{patch}"

if input(f"Old version: {old_version}\nNew Version: {new_version}\nConfirm [y/N]").lower().strip() == "y":
    with open(VERSION_PATH, "w") as f:
        f.write(new_version)
    print(f"Updated version number in {VERSION_PATH} to {new_version}")
    subprocess.run(["git", "add", VERSION_PATH])
    subprocess.run(["git", "commit", "-m", f"Update version to {new_version}"])
    subprocess.run(["git", "tag", "-a", f"v{new_version}", "-m", f"Version {new_version}"])
    subprocess.run(["git", "push", "origin", "--tags"])

else:
    print("Aborting...")
    sys.exit()
