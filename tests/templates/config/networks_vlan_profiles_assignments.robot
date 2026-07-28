
*** Settings ***
Library    String
Library    ../myutils.py

*** Test Cases ***
{% for domain in meraki.domains | default([], true) %}
{% for organization in domain.organizations | default([], true) %}
{% for network in organization.networks | default([], true) %}
{% for assignment in network.vlan_profiles_assignments | default([], true) %}
{% for device in assignment.devices | default([], true) %}
Verify {{ organization.name }}/networks/{{ network.name }}/vlan_profiles_assignments/{{ assignment.vlan_profile_iname }}/devices/{{ device }}//vlan_profile_iname{% if assignment.vlan_profile_iname is defined %}
    [Setup]   Get Meraki Data   /networks/{networkId}/vlanProfiles/assignments/byDevice   ['{{ organization.name }}', '{{ network.name }}']   assignments
    ${device_assignment}=    Get List Item By Key   ${assignments}   name   {{ device }}
    Should Be Equal As Strings   ${device_assignment}[vlanProfile][iname]   {{ assignment.vlan_profile_iname }}

{% else %}
    Skip    assignment.vlan_profile_iname is not defined
{% endif %}
{% endfor %}
{% for stack in assignment.stacks | default([], true) %}
Verify {{ organization.name }}/networks/{{ network.name }}/vlan_profiles_assignments/{{ assignment.vlan_profile_iname }}/stacks/{{ stack }}//vlan_profile_iname{% if assignment.vlan_profile_iname is defined %}
    [Setup]   Get Meraki Data   /networks/{networkId}/vlanProfiles/assignments/byDevice   ['{{ organization.name }}', '{{ network.name }}']   assignments
    ${stack_assignment}=    Get List Item By Key   ${assignments}   stack.name   {{ stack }}
    Should Be Equal As Strings   ${stack_assignment}[vlanProfile][iname]   {{ assignment.vlan_profile_iname }}

{% else %}
    Skip    assignment.vlan_profile_iname is not defined
{% endif %}
{% endfor %}
{% endfor %}
{% endfor %}
{% endfor %}
{% endfor %}
