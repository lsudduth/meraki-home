
*** Settings ***
Library    String
Library    ../myutils.py

*** Test Cases ***
{% for domain in meraki.domains | default([], true) %}
{% for organization in domain.organizations | default([], true) %}
{% for network in organization.networks | default([], true) %}

{% set appliance_traffic_shaping_uplink_bandwidth_limits = network.appliance.traffic_shaping.uplink_bandwidth_limits | default(none) %}
Verify {{ organization.name }}/networks/{{ network.name }}/appliance.traffic_shaping.uplink_bandwidth_limits{% if appliance_traffic_shaping_uplink_bandwidth_limits is not none %}
    [Setup]   Get Meraki Data   /networks/{networkId}/appliance/trafficShaping/uplinkBandwidth   ['{{ organization.name }}', '{{ network.name }}']   appliance_traffic_shaping_uplink_bandwidth
    ${evaluated}=    Evaluate    {{ appliance_traffic_shaping_uplink_bandwidth_limits }}
    ${validated}=    Validate Subset     ${appliance_traffic_shaping_uplink_bandwidth}[bandwidthLimits]    ${evaluated}
    Should Be True   ${validated}

{% else %}
    Skip    appliance.traffic_shaping.uplink_bandwidth_limits is not defined
{% endif %}


{% endfor %}
{% endfor %}
{% endfor %}
