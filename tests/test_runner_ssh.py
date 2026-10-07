from unittest.mock import MagicMock

from botocore.exceptions import ClientError
import pytest

from deploy.runner_ssh import open_access, close_access


def test_opens_only_runner_ip_and_records_owned_rule(tmp_path):
    client = MagicMock()
    client.authorize_security_group_ingress.return_value = {
        "SecurityGroupRules": [{"SecurityGroupRuleId": "sgr-012abc"}]
    }
    output = tmp_path / "github-output"
    assert open_access(client, "sg-lab", "8.8.8.8", output, "123") == "sgr-012abc"
    permissions = client.authorize_security_group_ingress.call_args.kwargs["IpPermissions"][0]
    assert permissions["FromPort"] == permissions["ToPort"] == 22
    assert permissions["IpRanges"][0]["CidrIp"] == "8.8.8.8/32"
    assert output.read_text() == "rule_id=sgr-012abc\n"


def test_duplicate_rule_is_preserved(tmp_path):
    client = MagicMock()
    client.authorize_security_group_ingress.side_effect = ClientError(
        {"Error": {"Code": "InvalidPermission.Duplicate"}}, "AuthorizeSecurityGroupIngress"
    )
    output = tmp_path / "github-output"
    assert open_access(client, "sg-lab", "8.8.8.8", output, "123") is None
    assert not output.exists()
    client.revoke_security_group_ingress.assert_not_called()


@pytest.mark.parametrize("ip", ["0.0.0.0/0", "127.0.0.1", "10.0.0.1", "::1", "invalid"])
def test_rejects_invalid_or_non_public_source_before_aws_call(tmp_path, ip):
    client = MagicMock()
    with pytest.raises(ValueError):
        open_access(client, "sg-lab", ip, tmp_path / "output", "123")
    client.authorize_security_group_ingress.assert_not_called()


def test_output_failure_removes_newly_created_rule(tmp_path):
    client = MagicMock()
    client.authorize_security_group_ingress.return_value = {
        "SecurityGroupRules": [{"SecurityGroupRuleId": "sgr-012abc"}]
    }
    with pytest.raises(OSError):
        open_access(client, "sg-lab", "8.8.8.8", tmp_path, "123")
    client.revoke_security_group_ingress.assert_called_once_with(
        GroupId="sg-lab", SecurityGroupRuleIds=["sgr-012abc"]
    )


def test_cleanup_removes_only_recorded_rule():
    client = MagicMock()
    close_access(client, "sg-lab", "sgr-012abc")
    client.revoke_security_group_ingress.assert_called_once_with(
        GroupId="sg-lab", SecurityGroupRuleIds=["sgr-012abc"]
    )
