import pytest
import paramiko
import time
from datetime import datetime
from pathlib import Path

# Test configuration
TEST_CONFIG = {
    "SELF_HOST": "192.168.20.10",
    "TEST_HOST": "192.168.20.11",
    "TEST_USER": "testadmin",
    "IDENTITY_FILE": "/home/devadmin/.ssh/id_rsa_testadmin",
    "LOG_FILE": "/var/log/icebox/icebox.log"
}


@pytest.fixture
def test_config():
    return TEST_CONFIG


@pytest.fixture
def ssh_client():
    """Fixture to create and manage SSH connections."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        TEST_CONFIG["TEST_HOST"],
        username=TEST_CONFIG["TEST_USER"],
        key_filename=TEST_CONFIG["IDENTITY_FILE"]
    )

    yield client
    client.close()


@pytest.fixture
def log_watcher():
    """Fixture to watch log files for specific patterns."""
    def wait_for_string(file_path, pattern, search_time, timeout=30, interval=1):
        start_time = time.time()
        log_file = Path(file_path)

        while True:
            if not log_file.exists():
                time.sleep(interval)
                if time.time() - start_time >= timeout:
                    pytest.fail(f"Timeout: File '{file_path}' not found after {timeout} seconds")
                continue

            with log_file.open('r') as f:
                lines = f.readlines()

            # Filter lines by timestamp and pattern
            for line in lines:
                try:
                    # Extract timestamp from log line [YYYY-MM-DD HH:MM:SS,MMM]
                    log_ts = line[1:20]
                    if log_ts >= search_time and pattern in line:
                        return line.strip()
                except IndexError:
                    continue

            if time.time() - start_time >= timeout:
                pytest.fail(f"Timeout: Pattern '{pattern}' not found after timestamp {search_time} in '{file_path}' after {timeout} seconds")

            time.sleep(interval)

    return wait_for_string