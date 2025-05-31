# Icebox

ICE (Intrusion Countermeasures Electronics) is a Cyberpunk concept for an active network defense system. Those in a Cyberpunk universe will presumably have a computer embedded in their bodies called a "Cyberdeck" which they may use to hack your network. ICE is designed to detect these attacks and counter-attack the attacker, resulting in their Cyberdeck frying, leaving them brain dead (or, preferably, actually dead).

We don't run around with computers in our heads yet. For now, Icebox is a suite of tools to monitor physical and logical networks and alert you about intrusions or lapses in defenses. It's an IDS with a fancy name, and it's proud of that.

Icebox is designed to be deployed on a Raspberry Pi, but you could probably run it in a VM. It is likely not compatible with Docker containers as multiple ice cubes depend on raw network access to log broadcast and multicast traffic.

## Ice Cubes

Individual features in Icebox are divided into "ice cubes."

### Icepick

Icepick "picks" away at network segmentation checks -- it is designed to continuously verify network connectivity, or lack of connectivity, to TCP endpoints. You configure a list of network endpoints which should not be accessible from the network in which the Icebox is deployed. Every 60-90 seconds, Icepick will attempt to establish a TCP connection with the endpoints and will notify you if any of the connections succeed.

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

While Ubuntu Server 22.04 is the only officially supported platform, you can install Icebox on other platforms with this:

```
curl -s https://raw.githubusercontent.com/icewatch-io/icebox/main/setup.sh | sudo bash -s -- --force
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

## Icewatch Configuration

The Icebox configuration options below can optionally be managed through Icewatch, a service to monitor and manage your Iceboxes from the cloud. Place an Icewatch config file in the Icebox config directory to have Icewatch override the local config and pull the Icebox config from Icewatch. Sign up for Icewatch at [https://icewatch.io](icewatch.io).

The Icewatch client looks for a configuration file in `/etc/icebox/icewatch.json`.

Example:

```json
{
  "api_url": "https://api.icewatch.io",
  "device_id": "da9af54c-92b5-404a-97d9-034fa3ce4c4a",
  "api_key": "CA89FB2A6DFD20527CDDD736D2BD564C0918290F55AC3A08F0C9113FE5636144"
}
```

All of the following are required:

#### api_url

The URL to use for the Icewatch API. Will be `https://api.icewatch.io` unless
you are participating in a bata.

#### device_id

The ID of an Icebox created in Icewatch.

#### api_key

The API key of the same Icebox in Icewatch.

## Icebox Configuration

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
  "alert_filters": [
    {
      "source": "snowdog",
      "subject": "",
      "body": "67"
    }
  ],
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

SMTP settings can be configured to allow the Icebox to send email notifications.

> NOTE: `SMTP` options are not supported in Icebox configs hosted in Icewatch.

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

## Alert filters

Alert filters can be used to silence noisy or expected alerts in your environment. The filter will not take any action unless either the `subject` or `body` option is set. If both are set, an alert must match both to be filtered.

Alert filter config options include the following:

```json
"alert_filters": [
  {
    "source": "snowdog",
    "subject": "",
    "body": "67"
  }
]
```

#### source

The source of the module from which to silence the alert.

#### subject

A substring to match in the alert's subject.

#### body

A substring to match in the alert's body.

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

# Development

## Running Tests

Icebox has unit tests to verify functionality during development. To run the tests, first install the development dependencies:

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

## Feature Ideas

### IP Address Hopping

Have Icebox change the device's IP address periodically to unpredictably move around the network.

### MAC Address Changing

Have Icebox change the device's MAC address on install (or periodically) so it is more or less likely to attract attention, depending on what you're after.

### Alert on DHCP Leases

Have Snowdog alert on new DHCP leases, giving admins a head start and an IP address to investigate when new devices join the network.

### Ice Shelf

Open a remote shell into your Iceboxes using Icewatch -- a foothold of sorts.

### Signals Intelligence

If installed on a Raspberry Pi or similar device, Icebox should have access to Bluetooth and Wireless chipsets. These could be used by Icebox to monitor for and alert on signal sources. This could allow detection of a phone or laptop within the physical vicinity of the Icebox without the device needing to probe the Icebox or join the protected network.

Such alarms could say:

`A device was observed searching for wireless network "Corp" in the vicinity of icebox1`

### Physical Sensors/Access Control

If installed on a Raspberry Pi or similar device, Icebox should have access to GPIO pins which allow physical sensors and access control devices to be installed. Icebox could utilize these to detect and alert on physical environment conditions, such as motion or light changes. Icebox could also be used to monitor and control access control devices such as door locks.

## Namestorming

Put feature names here if you've thought of them but not the feature yet.

- Snowdrift
- Snowplow
- Icewall/Ice Wall
