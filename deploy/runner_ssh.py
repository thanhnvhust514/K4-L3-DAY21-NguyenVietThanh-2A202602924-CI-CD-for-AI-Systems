"""Temporarily allow the current GitHub runner to SSH into the lab EC2."""

import argparse
from ipaddress import IPv4Address
import os
from pathlib import Path
import re
from urllib.request import urlopen

import boto3
from botocore.exceptions import ClientError


def open_access(client, group_id, runner_ip, output_path, run_id):
    ip = IPv4Address(runner_ip)
    if not ip.is_global:
        raise ValueError("Runner IP must be a public IPv4 address")
    cidr = f"{ip}/32"
    try:
        response = client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[{
                "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                "IpRanges": [{"CidrIp": cidr, "Description": f"Income lab GitHub run {run_id}"}],
            }],
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
            raise
        print(f"SSH already allows {cidr}; preserving the existing rule.")
        return None
    rule_id = response["SecurityGroupRules"][0]["SecurityGroupRuleId"]
    try:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"rule_id={rule_id}\n")
    except OSError:
        close_access(client, group_id, rule_id)
        raise
    print(f"Temporarily allowed SSH from {cidr}: {rule_id}")
    return rule_id


def close_access(client, group_id, rule_id):
    if not re.fullmatch(r"sgr-[0-9a-f]+", rule_id):
        raise ValueError("Invalid security group rule ID")
    client.revoke_security_group_ingress(GroupId=group_id, SecurityGroupRuleIds=[rule_id])
    print(f"Removed temporary SSH rule: {rule_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["open", "close"])
    args = parser.parse_args()
    group_id = os.environ["SERVER_SECURITY_GROUP_ID"]
    client = boto3.client("ec2")
    if args.operation == "open":
        with urlopen("https://checkip.amazonaws.com", timeout=10) as response:
            runner_ip = response.read(64).decode("ascii").strip()
        open_access(client, group_id, runner_ip, os.environ["GITHUB_OUTPUT"], os.environ["GITHUB_RUN_ID"])
    else:
        close_access(client, group_id, os.environ["SSH_RULE_ID"])


if __name__ == "__main__":
    main()
