from nornir.core import InitNornir
from nornir.core import Nornir
from nornir.plugins.tasks.connections import napalm_connection
#from nornir.plugins.functions.text import print_result
from nornir.core.inventory import Inventory
from nornir.plugins.tasks.networking import napalm_get
from prettytable import PrettyTable
from yaml import dump
import sys
import getopt
import getpass




def adapt_host_data(host):
    '''
    Inventory data transfoirmation
    '''
    if 'ansible_host' in host.data:
        host.data['nornir_host'] = host.data['ansible_host']

def insert_credentials(nr_inst, username, password):
    for host_obj in nr_inst.inventory.hosts.values():
        host_obj.data["nornir_username"] = username
        host_obj.data["nornir_password"] = password
    return nr_inst

def filter_is_group_child_of_group(nrgroup, group_name):
    ''' Nornir invetory filter
    Is nrgroup child of group_name
    
    :param nrgroup: nornir group
    :type nrgroup: nornir.inventory.group
    :param group_name: name of inventory group
    :type group_name: string
    :return: is group child of group_name ?
    :rtype: boolean
    '''

    if 'groups' in nrgroup: # if nrgroup contains attribute 'group'
        for actgroup in nrgroup['groups']:  # go through all group entries
            if actgroup == group_name:  # is it group_name we are searching for?
                return True
            if filter_is_group_child_of_group(nrgroup.nornir.inventory.groups[actgroup], group_name): # search for group_name recursively in parents
                return True
    return False

def filter_is_host_child_of_group(nrhost, group_name):
    '''Nornir inventory filter
    Is nrhost child of group_name?
    
    :param nrhost: nornir host
    :type nrhost: nornir.inventory.host
    :param group_name: name of inventory group
    :type group_name: string
    :return: is host child of group_name ?
    :rtype: boolean
    '''

    
    if 'groups' in nrhost:      # if nrhost contains 'groups' attribute
        for actgroup in nrhost['groups']:   # go through all entries
            if actgroup == group_name:  # is it group_name we are searching for?
                return True
            if filter_is_group_child_of_group(nrhost.nornir.inventory.groups[actgroup], group_name):    # search for group_name in parents
                return True
 
    return False
def normaize_mac(mac_addr):
    ''' Removes ':' and '.' from MAC address. Hex codes transforms to lowercases
    
    :param mac_addr: MAC address (or part of)
    :type mac_addr: string
    :return: MAC address
    :rtype: string
    '''

    mac_addr = mac_addr.replace(":","").replace(".","")
    mac_addr = mac_addr.lower()
    return mac_addr

def printtable(titles, table, format='pretty'):

    if format == 'pretty':
        outtable = PrettyTable()
        outtable.field_names = titles
        for line in table:
            outtable.add_row(line)
        print(outtable)

def init_connection(nr_object):
    ssh_cfg = nr_object.config.ssh_config_file
    result = nr_object.run(
                name="Connect using Napalm",
                task=napalm_connection,
                optional_args={'ssh_config_file': ssh_cfg}
        )
    for node in result.items():
            if node[1].failed:
                print('Error: connection to '+ node[0] + ' failed')
                print(node[1][0].result)


def find_mac_address(nr_set, search_mac, print_format='pretty'):

    result_mac = nr_set.run(napalm_get, getters=['get_mac_address_table'])
    for node in result_mac.items():
        if node[1].failed:
            print('Error: nornir run method to ' + node[0] + ' using '+ node[1].name + ' failed')
    list_to_print = []
    for node in result_mac.keys():
        if not result_mac[node].failed:
            for task_output in result_mac[node][0].result.items():
                for entry in task_output[1]:
                    if search_mac in normaize_mac(entry['mac']):
                        list_to_print.append([node, entry['mac'], entry['interface']])
    printtable(['node','mac_addr','interface'], list_to_print, print_format)

def find_description_iface(nr_set, description, print_format='pretty'):
    
    result = nr_set.run(napalm_get, getters=['get_interfaces'])
    for node in result.items():
        if node[1].failed:
            print('Error: nornir run method to ' + node[0] + ' using '+ node[1].name + ' failed')
    list_to_print = []
    for node in result.keys():
        if not result[node].failed:
            for task_output in result[node][0].result.items():
                for entry in task_output[1].keys():
                    if description.lower() in task_output[1][entry]['description'].lower():
                        list_to_print.append([node, entry, task_output[1][entry]['description']])
    printtable(['node','interface','description'], list_to_print, print_format)


def main():
    argv = sys.argv[1:]
    username = ''
    pswd = ''
    inventory_file = 'hosts.yml'
    debug = False
    command = ''
    group = ''
    description = ''
    output_format = ''

    usage_str = '''
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
    '''

    try:
        opts, args = getopt.getopt(argv, "dhp:u:g:c:m:s:i:o:", ["debug", "help", "password=", "username=", "group=", "command=", "mac=", "desc=", "inventory=", "output="]) # : require argument
    except getopt.GetoptError:
        print(usage_str)
        sys.exit(2)
    if not opts:                    # no arguments
        print(usage_str)
        sys.exit()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(usage_str)
            sys.exit()
        elif opt in ("-d", "--debug"):
            debug = True
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-g", "--group"):
            group = arg
        elif opt in ("-p", "--password"):
            pswd = arg
        elif opt in ("-c", "--command"):    # mac, desc
            command = arg
        elif opt in ("-m", "--mac"):
            search_mac = arg
        elif opt in ("-s", "--desc"):
            description = arg
        elif opt in ("-i", "--inventory"):
            inventory_file = arg
        elif opt in ("-o", "--output"):
            output_format = arg

    if not command:
        print("Command not specified")
        sys.exit(2)
    if not group:
        print("Group not specified")
        sys.exit(2)
    else:
        if command == 'mac':
            if not search_mac:
                print("MAC address or part not specified")
                sys.exit(2)
        if command == 'desc':
            if not description:
                print("Interface description not specified")
                sys.exit(2)
    if not username:
        print("Username not specified")
        sys.exit(2)
    if output_format:
        if output_format in ['y','Y','yaml','YAML']:
            output_format = 'yaml'
        else:
            print("Wrong output format specified")
            sys.exit(2)
    else:
        output_format = 'pretty'

    if pswd == '':
        pswd = getpass.getpass('Password:')
    

    nr = InitNornir(num_workers=100,
                  transform_function=adapt_host_data,
                  inventory="nornir.plugins.inventory.ansible.AnsibleInventory",
                  AnsibleInventory={"hostsfile": inventory_file})

    nr = insert_credentials(nr, username, pswd)

    nr_subset = nr.filter(filter_func=filter_is_host_child_of_group, group_name=group)

    init_connection(nr_subset)

    if command == 'mac':
        search_mac = normaize_mac(search_mac)
        find_mac_address(nr_subset, search_mac)
    elif command == 'desc':
        find_description_iface(nr_subset, description)





if __name__ == "__main__":

    main()

