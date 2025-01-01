# Icebox
ICE (Intrusion Countermeasures Electronics) is a Cyberpunk concept for an active network defense system. Those in a Cyberpunk universe will presumably have a computer embedded in their bodies called a "Cyberdeck" which they may use to hack your network. ICE is designed to detect these attacks and counter-attack the attacker, resulting in their Cyberdeck frying, leaving them brain dead (or, preferably, actually dead).

We don't run around with computers in our heads yet. For now, Icebox is a suite of tools to monitor physical and logical networks and alert you about intrusions or lapses in defenses. It's an IDS with a fancy name, and it's proud of that.

Icebox is designed to be deployed on a Raspberry Pi, but you could probably run it in a VM. It is likely not compatible with Docker containers as multiple modules depend on raw network access to log broadcast and multicast traffic.

## Ice Cubes
Individual features in Icebox are divided into "ice cubes."

### Icepick
Icepick "picks" away at network segmentation checks -- it is designed to continuously verify network segmentation. You configure a list of network endpoints which should not be accessible from the network in which Icebox is deployed. Every 60-90 seconds, Icepick will attempt to establish a TCP connection with the endpoints and will notify you if any of the connections succeed.

You can also configure Icepick to alert when a given endpoint is NOT accessible, sort of like an uptime check.

### Icicle
Icicles are fragile creations which break easily upon contact, alerting others to your presence. Similarly, Icicle silently waits for incoming connections and alerts you when it is touched. This can give you an early alert when devices are probing or scanning your network.

### Snowdog
Dogs are notoriously noisy creatures. They are often sought after for their ability to detect newcomers from afar and alert their owners. Similarly, Snowdog monitors iptables logs for broadcast and multicast traffic involving yet-unknown MAC addresses.

Snowdog has a "learning" mode where it records all observed MAC addresses. Once taken out of learning mode, Snowdog will instead alert on unrecognized MAC addresses (and then "learn" them to stop the alerts).

## Supported Operating Systems
Icebox officially supports only Ubuntu Server 22.04 (and minor versions). You can modify the setup script to install on other systems at your own risk.

## Installation
You can install Icebox on Ubuntu 22.04 systems with the following command:
```
curl -s https://raw.githubusercontent.com/icewatch-io/icebox/main/setup.sh | sudo bash
```

## Working with the service

### Starting Icebox
You can start Icebox using its systemd service:
```
systemctl start icebox
```

### Stopping Icebox
You can stop Icebox using its systemd service:
```
systemctl stop icebox
```

### Restarting Icebox
You can restart Icebox using its systemd service:
```
systemctl start icebox
```

## Testing
To run the tests, first install the development dependencies:

```bash
pip3 install -e .
```
Ensure pytest is installed:

```bash
pip3 install pytest
```

Run the tests using pytest:

```bash
python3 -m pytest
```

The tests require:
- A test host (default: 192.168.20.11) with SSH access
- A test user with SSH key authentication configured
- Appropriate permissions to execute commands on the test host

Configure test parameters in `tests/conftest.py` if needed.

## Configuration
Icebox looks for a configuration file in `/etc/icebox/icebox.json`.

Example:
```
{
  "icebox": {
    "name": "icebox1"
  },
  "log": {
    "level": "INFO",
    "file": "/var/log/icebox/icebox.log"
  },
  "iptables": {
    "log_file": "/var/log/kern.log"
  },
  "smtp": {
    "sending_enabled": true,
    "to": "admin@mycompany.com",
    "from": "admin@mycompany.com",
    "smtp_server": "email-smtp.us-west-2.amazonaws.com",
    "smtp_user": "AKIAXXXXXXXXXXX",
    "smtp_password": "xxxxxxxxxxxxx",
    "tls": true
  },
  "snowdog": {
    "learning": true,
    "db_file": "/opt/icebox/snowdog.sqlite",
    "alerting": false
  },
  "icepick": [
    {
      "name": "HTTPS from PROD to MGMT",
      "host": "10.20.30.1",
      "port": "443",
      "failure_action": "pass",
      "success_action": "email"
    },
    {
      "name": "HTTPS from PROD to ISOLATE1",
      "host": "10.0.88.1",
      "port": "443",
      "failure_action": "pass",
      "success_action": "email"
    }
  ]
}
```

### Icebox
Icebox config options include the following:
```
"icebox": {
  "name": "ICEBOX_NAME"
}
```

#### name
The name of the Icebox. This will appear in alerts and can be named after the network that it is protecting.

### Log
Log config options include the following:
```
"log": {
  "level": "INFO",
  "file": "/var/log/icebox/icebox.log"
}
```

#### level
The message level to save to the log file. Valid levels are `DEBUG`, `INFO`, `WARNING`, and `ERROR`.

#### file
The file in which to save log messages.

### Iptables
Iptables config options include the following:
```
"iptables": {
  "log_file": "/var/log/kern.log"
}
```

#### log_file
The log file to check for Icepick and Snowdog iptables log entries.

### SMTP
SMTP config options include the following:
```
"smtp": {
  "sending_enabled": true,
  "to": "admin@mycompany.com",
  "from": "admin@mycompany.com",
  "smtp_server": "email-smtp.us-west-2.amazonaws.com",
  "smtp_user": "AKIAXXXXXXXXXXX",
  "smtp_password": "xxxxxxxxxxxxx",
  "tls": true
}
```

#### sending_enabled
Whether to actually send the alert emails. Alerts will only be logged locally if set to false.

#### to
The email address to send the alert to, e.g. `foo@example.com`.

#### from
The email address to use as the "from" address in alerts, e.g. `foo@example.com`.

#### smtp_server
The SMTP server to use.

#### smtp_user
The SMTP user to use.

#### smtp_password
The SMTP password to use.

#### tls
Whether to use STARTTLS when connecting to the SMTP server.

### Snowdog
Snowdog config options include the following:
```
"snowdog": {
  "learning": true,
  "db_file": "/opt/icebox/snowdog.sqlite",
  "alerting": false
}
```

#### learning
Whether to enable learning mode. In learning mode, Snowdog will record all MAC addresses observed on the network. With leaning mode turned off, Snowdog will send an alert the first time a new MAC address is observed, and then record the MAC address to stop the alerts.

#### db_file
The path to an SQLite DB to which MAC addresses should be recorded. The DB will be created if not already present at the given path.

#### alerting
Whether to send alerts. If set to false, Snowdog will behave as described above, but will only log observations instead of sending an alert.

## Icepick
Icepick config options include the following:
```
"icepick": [
  {
    "name": "CHECK_NAME",
    "host": "1.2.3.4",
    "port": "443",
    "failure_action": "pass",
    "success_action": "email"
  }
]
```

The config consists of an array of checks TCP connections checks to perform. Icepick checks have the following config options, all of which are required:

#### name
The name of the check. This will appear in email alerts and should describe what is being checked, e.g. "HTTPS from PROD to WEBSITE".

#### host
The hostname or IP address to check the connection to.

#### port
The TCP port on the host to check the connection to.

#### failure_action
The action to take if the TCP connection fails. Valid actions are `pass` and `email`. `pass` means that no action should be taken. `email` means that an email alert should be sent.

#### success_action
Same as failure_action, but determines the action to take if the connection succeeds.

## Feature Ideas

### IP Address Hopping
Have Icebox change the device's IP address periodically to unpredictably move around the network.

### MAC Address Changing
Have Icebox change the device's MAC address on install (or periodically) so it is more or less likely to attract attention, depending on what you're after.

### Alert on DHCP Leases
Have Snowdog alert on new DHCP leases, giving admins a head start and an IP address to investigate when new devices join the network.

### Ice Watch
Have Icebox pull its config from the cloud and report alarm triggers to the cloud. Have the cloud send alerts.

### Ice Shelf
Open a remote shell into your Iceboxes using Ice Watch -- a foothold of sorts.

### Signals Intelligence
If installed on a Raspberry Pi or similar device, Icebox should have access to Bluetooth and Wireless chips. These could be used by Icebox to monitor for and alert on signal sources. This could allow detection of a phone or laptop within the physical vicinity of the Icebox without the device needing to probe the Icebox or join the protected network.

Such alarms could say:

`A device was observed searching for wireless network "Corp" in the vicinity of icebox1`

### Physical Sensors/Access Control
If installed on a Raspberry Pi or similar device, Icebox should have access to GPIO pins which allow physical sensors and access control devices to be installed. Icebox could utilize these to detect and alert on physical environment conditions, such as motion or light changes. Icebox could also be used to monitor and control access control devices such as door locks.

# Namestorming

Put feature names here if you've thought of them but not the feature yet.

- Snowdrift
- Snowplow
- Icewall/Ice Wall

