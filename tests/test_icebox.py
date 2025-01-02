import pytest
import paramiko
import time
from datetime import datetime, timezone
from pathlib import Path


def test_ping_detection(test_config, ssh_client, log_watcher):
    """Test ping detection functionality."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:23]

    # Execute ping command
    stdin, stdout, stderr = ssh_client.exec_command(
        f"ping -c 1 {test_config['SELF_HOST']}"
    )
    stdout.channel.recv_exit_status()

    # Check for expected log entries
    ping_log = log_watcher(test_config["LOG_FILE"], "PING DETECTED", timestamp)
    email_log = log_watcher(test_config["LOG_FILE"], "Email sent successfully", timestamp)

    assert ping_log is not None, "Ping detection log entry not found"
    assert email_log is not None, "Email notification log entry not found"


def test_port_scan_detection(test_config, ssh_client, log_watcher):
    """Test port scan detection functionality."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:23]

    # Execute Nmap scan
    stdin, stdout, stderr = ssh_client.exec_command(
        f"nmap -p 100-120 {test_config['SELF_HOST']}"
    )
    stdout.channel.recv_exit_status()

    # Check for expected log entries
    scan_log = log_watcher(test_config["LOG_FILE"], "PORT SCAN DETECTED", timestamp)
    email_log = log_watcher(test_config["LOG_FILE"], "Email sent successfully", timestamp)

    assert scan_log is not None, "Port scan detection log entry not found"
    assert email_log is not None, "Email notification log entry not found"


def test_tcp_connection_detection(test_config, ssh_client, log_watcher):
    """Test TCP connection detection functionality."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f")[:23]

    # Execute Netcat command
    stdin, stdout, stderr = ssh_client.exec_command(
        f"nc {test_config['SELF_HOST']} 8434"
    )
    stdout.channel.recv_exit_status()

    # Check for expected log entries
    ping_log = log_watcher(test_config["LOG_FILE"], "Incoming connection detected", timestamp)
    email_log = log_watcher(test_config["LOG_FILE"], "Email sent successfully", timestamp)

    assert ping_log is not None, "TCP connection detection log entry not found"
    assert email_log is not None, "Email notification log entry not found"

