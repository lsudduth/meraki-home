
*** Settings ***
Library    ../myutils.py

*** Test Cases ***
{% set day_of_week_map = {'sunday': 'Sun', 'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed', 'thursday': 'Thu', 'friday': 'Fri', 'saturday': 'Sat'} %}
{% set product_name_map = {'switch_catalyst': 'switchCatalyst', 'cellular_gateway': 'cellularGateway'} %}
{% for domain in meraki.domains | default([], true) %}
{% for organization in domain.organizations | default([], true) %}
{% for network in organization.networks | default([], true) %}

{% if network.firmware is defined %}
{% set upgrade_products = network.firmware.upgrade.products | default({}, true) %}
{% set downgrade_products = network.firmware.downgrade.products | default({}, true) %}
{% set automatic_upgrade_window = network.firmware.automatic_upgrade_window | default({}, true) %}

{% for product_name, product_data in upgrade_products.items() %}
{% set api_product = product_name_map.get(product_name, product_name) %}
Verify {{ organization.name }}/networks/{{ network.name }}/firmware.upgrade.products.{{ product_name }}.next_upgrade.to_version{% if product_data.next_upgrade.to_version is defined %}
    [Setup]    Get Meraki Data    /networks/{networkId}/firmwareUpgrades    ['{{ organization.name }}', '{{ network.name }}']    fw_upgrades
    ${current_version}=    Set Variable    ${fw_upgrades}[products][{{ api_product }}][currentVersion][shortName]
    ${next_upgrade_version}=    Evaluate    ($fw_upgrades['products']['{{ api_product }}'].get('nextUpgrade') or {}).get('toVersion', {}).get('shortName', '')
    Should Be True    '{{ product_data.next_upgrade.to_version }}' in ['${current_version}', '${next_upgrade_version}']    msg={{ product_data.next_upgrade.to_version }} not found in currentVersion.shortName or nextUpgrade.toVersion.shortName for {{ product_name }}
{% else %}
    Skip    firmware.upgrade.products.{{ product_name }}.next_upgrade.to_version is not defined
{% endif %}

Verify {{ organization.name }}/networks/{{ network.name }}/firmware.upgrade.products.{{ product_name }}.participate_in_next_beta_release{% if product_data.participate_in_next_beta_release is defined %}
    [Setup]    Get Meraki Data    /networks/{networkId}/firmwareUpgrades    ['{{ organization.name }}', '{{ network.name }}']    fw_upgrades
    Should Be Equal As Strings    ${fw_upgrades}[products][{{ api_product }}][participateInNextBetaRelease]    {{ product_data.participate_in_next_beta_release }}
{% else %}
    Skip    firmware.upgrade.products.{{ product_name }}.participate_in_next_beta_release is not defined
{% endif %}

{% endfor %}

{% for product_name, product_data in downgrade_products.items() %}
{% set api_product = product_name_map.get(product_name, product_name) %}
Verify {{ organization.name }}/networks/{{ network.name }}/firmware.downgrade.products.{{ product_name }}.next_downgrade.to_version{% if product_data.next_downgrade.to_version is defined %}
    [Setup]    Get Meraki Data    /networks/{networkId}/firmwareUpgrades    ['{{ organization.name }}', '{{ network.name }}']    fw_upgrades
    ${current_version}=    Set Variable    ${fw_upgrades}[products][{{ api_product }}][currentVersion][shortName]
    ${next_upgrade_version}=    Evaluate    ($fw_upgrades['products']['{{ api_product }}'].get('nextUpgrade') or {}).get('toVersion', {}).get('shortName', '')
    Should Be True    '{{ product_data.next_downgrade.to_version }}' in ['${current_version}', '${next_upgrade_version}']    msg={{ product_data.next_downgrade.to_version }} not found in currentVersion.shortName or nextUpgrade.toVersion.shortName for {{ product_name }}
{% else %}
    Skip    firmware.downgrade.products.{{ product_name }}.next_downgrade.to_version is not defined
{% endif %}

{% endfor %}

Verify {{ organization.name }}/networks/{{ network.name }}/firmware/automatic_upgrade_window/day_of_week{% if automatic_upgrade_window.day_of_week is defined %}
    [Setup]    Get Meraki Data    /networks/{networkId}/firmwareUpgrades    ['{{ organization.name }}', '{{ network.name }}']    fw_upgrades
    Should Be Equal As Strings    ${fw_upgrades}[upgradeWindow][dayOfWeek]    {{ day_of_week_map[automatic_upgrade_window.day_of_week] }}
{% else %}
    Skip    firmware.automatic_upgrade_window.day_of_week is not defined
{% endif %}

Verify {{ organization.name }}/networks/{{ network.name }}/firmware/automatic_upgrade_window/hour_of_day{% if automatic_upgrade_window.hour_of_day is defined %}
    [Setup]    Get Meraki Data    /networks/{networkId}/firmwareUpgrades    ['{{ organization.name }}', '{{ network.name }}']    fw_upgrades
    Should Be Equal As Strings    ${fw_upgrades}[upgradeWindow][hourOfDay]    {{ automatic_upgrade_window.hour_of_day }}
{% else %}
    Skip    firmware.automatic_upgrade_window.hour_of_day is not defined
{% endif %}

{% endif %}
{% endfor %}
{% endfor %}
{% endfor %}
