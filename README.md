# BETA SOFTWARE
Icebox is currently in Beta. Expect significant changes before an initial release.

# Icebox
ICE (Intrusion Countermeasures Electronics) is a Cyberpunk concept for an active network defense system. Those in a Cyberpunk universe will presumably have a computer embedded in their bodies called a "Cyberdeck" which they may use to hack your network. ICE is designed to detect these attacks and counter-attack the attacker, resulting in their Cyberdeck frying, leaving them brain dead (or, preferably, actually dead).

We don't run around with computers in our heads quite yet. For now, Icebox is a suite of tools to monitor physical and logical networks and alert you about intrusions or lapses in defenses. It's an IDS with a fancy name, and it's proud of that.

Icebox is designed to be deployed on a Raspberry Pi, but you could probably run it in a VM. It is likely not compatible with Docker containers as multiple modules depend on raw network access to log broadcast and multicast traffic.

## Ice Cubes
Independent features in Icebox are divided into "ice cubes."

### Icepick
Icepick "picks" away at network segmentation checks -- it is designed to continuously verify network segmentation. You configure a list of network endpoints which should not be accessible from the network in which Icebox is deployed. Every 60-90 seconds, Icebox will attempt to establish a TCP connection with the endpoints and will notify you if any of the connections succeed.

You can also configure Icepick to alert when a given endpoint is NOT accessible, sort of like an uptime check.

### Icicle
Icicles are fragile creations which break easily upon contact, alerting others to your presence. Similarly, Icicle silently waits for incoming connections and alerts you when it is touched. This can give you an early alert when devices are probing or scanning your network.

### Snowdog
Dogs are notoriously noisy creatures. They are often sought after for their ability to detect newcomers from afar and alert their owners. Similarly, Snowdog monitors iptables logs broadcast and multicast traffic involving yet-unknown MAC addresses.

Snowdog has a "learning" mode where it records all observed MAC addresses. Once taken out of learning mode, Snowdog will instead alert on unrecognized MAC addresses (and then "learn" them to stop the alerts).

## Installation
You can install Icebox on Ubuntu 22.04 systems with the following command:
```
curl -s https://raw.githubusercontent.com/icewatch-io/icebox/main/setup.sh | sudo bash
```

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
Using Ice Watch, open a remote shell into your Iceboxes -- a foothold of sorts.

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

