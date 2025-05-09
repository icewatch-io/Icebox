#!/bin/bash

add_rules() {
    remove_rules

    if [ -z "$DEVICE_IP" ]; then
        DEVICE_IP=$(ip route get 1 | awk '{print $7; exit}')
    fi

    # ICICLE
    # Add logging rules for new TCP, UDP, and ICMP traffic to device IP
    iptables -A INPUT -d $DEVICE_IP -p tcp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "
    iptables -A INPUT -d $DEVICE_IP -p udp -m conntrack --ctstate NEW -j LOG --log-prefix "ICICLE: "
    iptables -A INPUT -d $DEVICE_IP -p icmp -j LOG --log-prefix "ICICLE: "

    # SNOWDOG
    # Add logging rules for broadcast, multicast, and anycast traffic
    iptables -A INPUT -m addrtype --dst-type BROADCAST -j LOG --log-prefix "SNOWDOG: "
    iptables -A INPUT -m addrtype --dst-type MULTICAST -j LOG --log-prefix "SNOWDOG: "
    iptables -A INPUT -m addrtype --dst-type ANYCAST -j LOG --log-prefix "SNOWDOG: "
}

remove_rules() {
    iptables -L INPUT --line-numbers |
        grep -E 'LOG.*(ICICLE|SNOWDOG): ' |
        awk '{print $1}' |
        sort -rn |
        while read -r rule_num; do
            iptables -D INPUT "$rule_num" 2>/dev/null || true
        done
}

case "$1" in
    add)
        add_rules
        ;;
    remove)
        remove_rules
        ;;
    *)
        echo "Usage: $0 {add|remove}"
        exit 1
        ;;
esac
