
*** Settings ***
Library    String
Library    ../myutils.py

*** Test Cases ***
{% for domain in meraki.domains | default([], true) %}
{% for organization in domain.organizations | default([], true) %}

{% set appliance_vpn_third_party_vpn_peers = organization.appliance.third_party_vpn_peers | default(none) %}
Verify {{ organization.name }}/appliance_vpn_third_party_vpn_peers/peers{% if appliance_vpn_third_party_vpn_peers is not none %}
    [Setup]   Get Meraki Data   /organizations/{organizationId}/appliance/vpn/thirdPartyVPNPeers   ['{{ organization.name }}']   appliance_vpn_third_party_vpn_peers
    ${evaluated}=    Evaluate    {{ appliance_vpn_third_party_vpn_peers }}
    ${validated}=    Validate Subset     ${appliance_vpn_third_party_vpn_peers}[peers]    ${evaluated}     ['name', 'public_ip', 'remote_id', 'local_id', 'secret', 'private_subnets', 'ipsec_policies.ike_cipher_algo', 'ipsec_policies.ike_auth_algo', 'ipsec_policies.ike_prf_algo', 'ipsec_policies.ike_diffie_hellman_group', 'ipsec_policies.ike_lifetime', 'ipsec_policies.child_cipher_algo', 'ipsec_policies.child_auth_algo', 'ipsec_policies.child_pfs_group', 'ipsec_policies.child_lifetime', 'ike_version', 'network_tags']
    Should Be True   ${validated}

{% else %}
    Skip    appliance_vpn_third_party_vpn_peers.peers is not defined
{% endif %}


{% endfor %}
{% endfor %}
