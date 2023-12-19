from ansible.plugins.vars import BaseVarsPlugin

class VarsModule(BaseVarsPlugin):

    def get_vars(self, loader, path, entities, cache=True):

        super(VarsModule, self).get_vars(loader, path, entities)
        data = {
            'bb_core_iceberg_naming': 'iceberg',
            'bb_core_equipment_naming': 'equipment',
            'bb_core_management_networks_naming': 'net',
            'bb_core_master_groups_naming': 'mg',
            'bb_core_managements_group_name': 'mg_managements',

            #############################################################
            ############ J2_ LOGIC
            #####

            ### Groups
            # List of master groups.
            'j2_master_groups_list': "{{ groups | select('match','^'+bb_core_master_groups_naming+'_.*') | list | unique | sort }}",
            # List of equipment groups.
            'j2_equipment_groups_list': "{{ (groups | select('match','^'+bb_core_equipment_naming+'_.*') | list | length | int > 0) | ternary(groups | select('match','^'+bb_core_equipment_naming+'_.*') | list | unique | sort, ['all']) }}",
            # Host current equipment group.
            'j2_node_equipment': "{{ (groups | select('match','^'+bb_core_equipment_naming+'_.*') | list | length | int > 0) | ternary(group_names | select('match','^'+bb_core_equipment_naming+'_.*') | list | unique | sort | first | default('') | replace(bb_core_equipment_naming + '_',''), 'all') }}",

            ## Equipments
            # Generate the list of nodes with their associated os and hw groups as values
            # Example:
            #   c001:
            #     hw: hw_supermicro_XXX
            #     os: os_ubuntu_22.04_gpu
            # This is a transverse j2 (j2_bb_), used as a cache fact
            'j2_bb_nodes_profiles': """
            {%- set nodes_ep_forward = {} -%}
            {%- for host in j2_hosts_range -%}
            {%- set host_hw = (hostvars[host]['group_names'] | select('match','^'+'hw'+'_.*') | list | unique | sort | first) | default(none, true) -%}
            {%- set host_os = (hostvars[host]['group_names'] | select('match','^'+'os'+'_.*') | list | unique | sort | first) | default(none, true) -%}
            {%- if host_hw is not none and host_os is not none -%}
            {%- set host_ep = (host_hw + '_' + host_os) -%}
            {%- else -%}
            {%- set host_ep = none -%}
            {%- endif -%}
            {%- set host_type = hostvars[host]['hw_equipment_type'] | default(none, true) -%}
            {%- do nodes_ep_forward.update({host: {'hw': host_hw, 'os': host_os, 'ep': host_ep, 'type': host_type}}) -%}
            {%- endfor -%}
            {{ nodes_ep_forward }}
            """,

            # Generate the equipments that are existing combination of hardware and os profiles
            # and store the list of associated nodes inside these equipments. Nodes without both hw_ and os_ are ignored.
            # Example:
            #   hw_supermicro_XXX_os_ubuntu_22.04_gpu:
            #     - c001
            # This is a transverse j2 (j2_bb_), used as a cache fact
            # It is expected that the dependency fact be bb_nodes_profiles
            # If the dependency fact was not already cached, it will not be used but that implies longuer calculations
            'j2_bb_equipments': """
            {%- set nodes_ep_reverse = {} -%}
            {%- if bb_nodes_profiles is defined -%}
            {%- set nodes_profile = bb_nodes_profiles -%}
            {%- else -%}{# Calculate since not cached #}
            {%- set nodes_profile = j2_bb_nodes_profiles -%}
            {%- endif -%}
            {%- for host, host_keys in nodes_profile.items() -%}
            {%- if host_keys['hw'] is not none and host_keys['os'] is not none -%}
                {%- set host_equipment = (host_keys['hw'] + '_' + host_keys['os']) -%}
                {%- if host_equipment not in nodes_ep_reverse -%}
                {%- do nodes_ep_reverse.update({host_equipment: []}) -%}
                {%- endif -%}
            {{ nodes_ep_reverse[host_equipment].append(host) }}
            {%- endif -%}
            {%- endfor -%}
            {{ nodes_ep_reverse }}
            """,

            ### Network

            ## Resolution
            # Resolution network. The network on which host can be ping by direct name. (ex: ping c001).
            'j2_node_main_resolution_network': "{{ network_interfaces[0].network | default(none) }}",
            # Resolution address.
            'j2_node_main_resolution_address': "{{ (network_interfaces[0].ip4 | default('')).split('/')[0] | default(none) }}",

            ## Main network
            # The network used by Ansible to deploy configuration (related to ssh).
            # Also the network used by the host to get services ip.
            'j2_node_main_network': "{{ network_interfaces | default([]) | selectattr('network','defined') | selectattr('network','match','^'+j2_current_iceberg_network+'-[a-zA-Z0-9]+') | map(attribute='network') | list | first | default(none) }}",
            # Main network interface. For consistency, we use j2_node_main_network as source.
            'j2_node_main_network_interface': "{{ network_interfaces[j2_node_main_network].interface | default(none) }}",
            # Main address, same concept.
            'j2_node_main_address': "{{ network_interfaces[j2_node_main_network].ip4 | default(none) }}",

            ## Other
            # List of management networks.
            'j2_management_networks': "{{ networks | select('match','^'+j2_current_iceberg_network+'-[a-zA-Z0-9]+') | list | unique | sort }}",

            ### Icebergs engine file
            # List all icebergs
            'j2_icebergs_groups_list': "{{ groups | select('match','^'+bb_core_iceberg_naming+'[a-zA-Z0-9]+') | list }}",
            # Get total number of icebergs
            'j2_number_of_icebergs': "{{ groups | select('match','^'+bb_core_iceberg_naming+'[a-zA-Z0-9]+') | list | length }}",
            # Grab current iceberg group
            'j2_current_iceberg': "{{ bb_icebergs_system | default(false) | ternary( group_names | select('match','^'+bb_core_iceberg_naming+'[a-zA-Z0-9]+') | list | unique | sort | first | default(bb_core_iceberg_naming+'1'), bb_core_iceberg_naming+'1') }}",
            # Grab current iceberg number
            'j2_current_iceberg_number': "{{ j2_current_iceberg | replace(bb_core_iceberg_naming,' ') | trim }}",
            # Grab current iceberg networks pattern
            'j2_current_iceberg_network': "{{ bb_icebergs_system | default(false) | ternary(bb_core_management_networks_naming + (j2_current_iceberg_number | string), bb_core_management_networks_naming) }}",
            # Generate list of managements connected to this iceberg from sub icebergs
            'j2_iceberg_sub_managements_members': "{% set range = [] %}{% for host in (groups[bb_core_managements_group_name] | default([])) %}{% if (hostvars[host]['bb_iceberg_master'] | default(none))  == j2_current_iceberg %}{{ range.append(host) }}{% endif %}{% endfor %}{{ range }}",
            # Generate range of hosts to include in current configurations
            'j2_hosts_range': "{{ ((bb_icebergs_system | default(false)) == true and (bb_iceberg_hosts_range | default('all')) == 'iceberg') | ternary( j2_iceberg_sub_managements_members + groups[j2_current_iceberg] | default([]), groups['all']) }}",
            # Generate a dict that contains host main network for each iceberg
            'j2_icebergs_main_network_dict': "{{ '{' }}{% for iceberg in (j2_icebergs_groups_list | default([])) %}{% if not loop.first %},{% endif %}'{{ iceberg }}':'{{ network_interfaces | default([]) | selectattr('network', 'defined') | selectattr('network', 'match', '^'+(bb_icebergs_system | default(false) | ternary(bb_core_management_networks_naming + (iceberg | replace(bb_core_iceberg_naming, ' ') | trim | string), bb_core_management_networks_naming) )+'-[a-zA-Z0-9]+') | map(attribute='network') | list | first | default(none) }}'{% endfor %}{{ '}' }}",
        }
        return data
    
