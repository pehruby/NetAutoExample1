
# Network Automation Example 1

Created for NetDevOps Live! Code Exchange Challenge

## getdevpar script

The script

- utilizes the Nornir (1.x) and NAPALM frameworks
- prints all interfaces of device inventory group which contain specified string in the description
- prints MAC address entries specified by the part of the MAC address for devices which are members of specified inventory group

Usage:

```text
    Prints specified devices parameters
    Usage: getdevpar.py [OPTIONS]
    -d,     --debug                     debug (opt.)
    -h,     --help                      display help (opt.)
    -i,     --inventory                 inventory file
    -g,     --group                     inventory group
    -u,     --username                  username
    -p,     --password                  password (opt.)
    -c,     --command                   command (mac, desc)
    -m,     --mac                       part of mac address (used with command 'mac')
    -s,     --desc                      part of description (used with command 'desc')
```

Examples:

```text
python3 getdevpar.py -i default_inventory.yaml -g access -c desc -s 'LX' -u cisco

python3 getdevpar.py -i default_inventory.yaml -g access -c mac -m '8014' -u cisco
```

## Python environment

Create virtual environment and activate it (optional)

```text
python3 -m venv venv
. venv/bin/activate
```

Install required modules

```text
pip install -r requirements.txt
```

## Create VIRL test environment (optional)

In .virl.rc file change the VIRL_HOST variable according to the IP/DNS name of your VIRL server

Create SSH keys on your workstation with empty password if you don't have it so far.

```text
ssh-keygen -r rsa
```

Update ~/.ssh/config

```text
host jumphost
  IdentityFile ~/.ssh/id_rsa
  # port 10000
  IdentitiesOnly yes
  user guest
  hostname 172.16.1.10
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null

host 10.255.0.*
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null
  ProxyCommand ssh jumphost nc %h %p

host 172.16.1.*         <- change this to the IP range of your Flat network
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null
```

Spin up the simulation

```text
virl up
```

VIRL simulation topology:

![alt text](https://github.com/pehruby/NetAutoExample1/blob/master/sketch.png "Topology")

Enter 'virl nodes' command and note External Address of your ~mgmt-lxc

```text
virl nodes
...
├───────────┼──────────┼─────────┼─────────────┼────────────┼──────────────────────┼────────────────────┤
│ ~mgmt-lxc │ mgmt-lxc │ ACTIVE  │ REACHABLE   │ ssh        │ 10.255.0.1           │ 172.16.1.10        │
├───────────┼──────────┼─────────┼─────────────┼────────────┼──────────────────────┼────────────────────┤
```

When the simulation is running (all nodes are in the ACTIVE state), create Ansible inventory file

```text
virl generate ansible
```

Update the inventory file (default_inventory.yaml)

```text
all:
  vars:
    ansible_network_os: ios
    nornir_nos: ios
    ansible_ssh_common_args: '-o ProxyCommand="ssh -W %h:%p guest@172.16.1.10"'  # set the IP address of your jump host (~lxc-flat, External Address)
    ansible_connection: network_cli
  children:
```

Copy ssh public key to the jumphost

```text
ssh-copy-id guest@172.16.1.10       <-password guest
```

Update ~/.ansible.cfg

```text
[defaults]
host_key_checking = False
```

Create VLANs etc using Ansible playbook (password is cisco)

```text
ansible-playbook -i default_inventory.yaml vlans.yaml -u cisco -k
```

Connect to lxc and check if other lxcs are reachable

```text
virl ssh lxc-11
cisco@10.255.0.11's password:   <- cisco

ping 10.0.0.11
ping 10.0.1.11
```

Now print all interfaces in the group access which have 'LX' in description

```text
(venv) vagrant@ubuntu-xenial:~/NetAutoExample1$ python3 getdevpar.py -i default_inventory.yaml -g access -c desc -s 'LX' -u cisco
Password:
+---------+--------------------+-------------+
|   node  |     interface      | description |
+---------+--------------------+-------------+
| access2 | GigabitEthernet0/2 |    LXC 21   |
| access2 | GigabitEthernet0/3 |    LXC 22   |
| access1 | GigabitEthernet0/2 |    LXC 11   |
| access1 | GigabitEthernet0/3 |    LXC 12   |
+---------+--------------------+-------------+
```

Print all entries from MAC address table which contain '8014' as a part of the MAC address

```text
venv) vagrant@ubuntu-xenial:~/NetAutoExample1$ python3 getdevpar.py -i default_inventory.yaml -g access -c mac -m '8014' -u cisco
Password:
+---------+-------------------+-----------+
|   node  |      mac_addr     | interface |
+---------+-------------------+-----------+
| access2 | 5E:00:00:02:80:14 |   Gi0/1   |
| access2 | 5E:00:00:03:80:14 |   Gi0/1   |
| access1 | 5E:00:00:02:80:14 |   Gi0/1   |
| access1 | 5E:00:00:03:80:14 |   Gi0/1   |
+---------+-------------------+-----------+
```

Connect to some node and check the ways how RSA keys on routers in VIRL are created.
Thanks to [sihart](https://community.cisco.com/t5/tools/generate-rsa-key-on-xr-in-virl-on-boot/td-p/3436035)

Shutdown the simulation

```text
virl down
```