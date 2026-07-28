#!/usr/bin/env python3

"""
# Terraform Import Generator

## Overview
An automated Terraform import generator that streamlines the process of importing
existing Meraki infrastructure into Terraform state management.

## Usage

1. Fetch current Meraki configuration using `nac-collector` to obtain `meraki.json`.
2. Convert the configuration to NaC-Meraki data model using `nac-tool` to obtain a directory with `.nac.yaml` files.
3. Create a Terraform configuration pointing to the data model directory (create a `main.tf` using `meraki` module).
4. Run `terraform plan` to make sure no errors appear at plan time for the converted model.
5. Run the import script in the directory with the `main.tf`, passing the `meraki.json`, to create `import.tf`:

```
$ /path/to/import.py /path/to/meraki.json
```

6. Run `terraform plan` to see what would be imported.

```
$ terraform plan
<...>
Plan: 676 to import, 65 to add, 509 to change, 0 to destroy.
```
Make sure there are no `to add` resources.
`65 to add` here means 65 resources were not matched by the script and not imported.
Applying this plan will fail since the resources already exist.

## Functionality
This tool generates import.tf configuration files by:

- **Data Model Processing**: Parses YAML and JSON data models from nac-tool and nac-collector
  to identify infrastructure resources that need to be imported
- **Resource Discovery**: Analyzes the data model to determine which Meraki
  resources should be brought under Terraform management
- **Import Configuration**: Leverages meraki.json metadata to map resources to
  their corresponding Terraform modules and generate accurate resource identifiers
- **Automation**: Creates complete import.tf files with proper resource references
  and import statements

## Input Sources
- **Data Model (YAML/JSON)**: Output from nac-tool containing infrastructure Configuration
- **meraki.json**: Metadata file containing Terraform module mappings and resource IDs from nac-collector

## Output
- **import.tf**: Complete Terraform import configuration file ready for execution
"""

import json
import sys
import subprocess
import logging

from pathlib import Path
from typing import Any

logger = logging.getLogger("nac_meraki_import")


CWD = Path.cwd()

IMPORT_TF_FILENAME = "import.tf"
IMPORT_TF_PATH = CWD / IMPORT_TF_FILENAME
IMPORT_PLAN_FILENAME = "import_plan.tfplan"
IMPORT_PLAN_PATH = CWD / IMPORT_PLAN_FILENAME
IMPORT_PLAN_JSON_FILENAME = "import_plan.json"
IMPORT_PLAN_JSON_PATH = CWD / IMPORT_PLAN_JSON_FILENAME


def preprocess_json(meraki_json: dict[str, Any]) -> None:
    """
    Preprocess Meraki JSON to make the structure closer to the NaC-Meraki Terraform module key hierarchy.
    """

    link_organization_devices_under_networks(meraki_json)
    link_org_data_under_networks(meraki_json)
    add_extra_resources(meraki_json)


# Copied from nac-tool
def link_organization_devices_under_networks(meraki_json: dict[str, Any]) -> None:
    for org in meraki_json.get("organization", []):
        org_children = org.get("children", {})

        devices = org_children.get("device", [])
        # If the API returned an error, this would be a dict instead of a list.
        # Skip this organization, as there are no devices to move.
        if not isinstance(devices, list):
            continue

        networks = org_children.get("network", [])
        if not isinstance(networks, list):
            logger.error(
                "Cannot link devices from organization %s (%s) under networks as fetching networks had failed: %s."
                + " Device configuration for this organization will not be in the data model."
                " Resolve the issue and rerun nac-collector.",
                org.get("data", {}).get("name", "<no name>"),
                org.get("data", {}).get("id", "<no id>"),
                networks.get("error", "<no error message>"),
            )
            continue

        networks_by_id = {
            network.get("data", {}).get("id", ""): network for network in networks
        }

        # Ensure all networks have at least an empty list of devices
        # to match what would have happened if the (deprecated) /networks/{id}/devices endpoint was used.
        for network in networks:
            network_children = network.setdefault("children", {})
            network_children.setdefault("device", [])

        for device in devices:
            network_id = device.get("data", {}).get("networkId")
            if network_id is None:
                # Should not happen - only devices assigned to a network are returned.
                logger.error(
                    "Cannot move device %s under its network - networkId is missing or null. The device's configuration will be ignored.",
                    device.get("data", {}).get("serial"),
                )
                continue
            network = networks_by_id.get(network_id)
            if network is None:
                # Should only happen in a race condition:
                # 1. networks are fetched (they are currently listed before devices in the generated endpoints/meraki.yaml),
                # 2. then a device is created and claimed into a new network,
                # 3. then devices are fetched - a device refers to a network that has not been fetched.
                logger.error(
                    "Cannot move device %s under its network %s as the network cannot be found. The device's configuration will be ignored.",
                    device.get("data", {}).get("serial"),
                    network_id,
                )
                continue
            network["children"]["device"].append(device)


# Copied from nac-tool
def link_org_data_under_networks(meraki_json: dict[str, Any]) -> None:
    """Move org-level endpoint data with split_by_network to respective networks.

    Some API endpoints have a network-level PUT but an organization-level GET
    that returns data for all networks in a flat list. Items with
    split_by_network=true (set by nac-collector) are moved to the corresponding
    network's children based on networkId.

    Note: This is different from device linking, which populates a list schema
    field by grouping multiple devices per network.
    """

    for org in meraki_json.get("organization", []):
        org_children = org.get("children", {})
        networks = org_children.get("network", [])

        if not isinstance(networks, list):
            continue

        networks_by_id = {
            network.get("data", {}).get("id", ""): network for network in networks
        }

        for endpoint_name, items in org_children.items():
            if not isinstance(items, list):
                continue

            for item in items:
                if not item.get("split_by_network"):
                    continue

                network_id = item.get("data", {}).get("networkId")
                if not network_id:
                    continue

                network = networks_by_id.get(network_id)
                if network is None:
                    logger.warning(
                        "Cannot move %s item under network %s - network not found.",
                        endpoint_name,
                        network_id,
                    )
                    continue

                network_children = network.setdefault("children", {})
                network_children[endpoint_name] = item


def add_extra_resources(meraki_json: dict[str, Any]) -> None:
    """
    Add custom resources to the JSON that are either not returned by the API or are collected as different resources.
    Also, adjust "terraform_import_ids" for special cases.
    Set "terraform_no_import" for resources not supported by the provider yet.

    Create even resource instances that have no reason to be created, e.g. network_device_claim when there are no devices -
    only necessary resources will be looked up in the JSON anyway -
    the terraform plan only has resources produced by nac-tool, and that, for example, omits empty ones.
    """

    for org in meraki_json.get("organization", []):
        org_id = org.get("data", {}).get("id")
        org_children = org.get("children", {})

        # GET endpoint is "organization_inventory_devices" instead.
        org_children["organization_inventory_claim"] = {
            "data": {},
            "terraform_import_ids": [org_id],
        }

        networks = get_list_or_empty(org_children, "network")
        for network in networks:
            network_children = network.setdefault("children", {})
            network_id = network.get("data", {}).get("id")

            # A single resource for all devices in the network
            # (which are fetched via "device" on organization level and grouped under networks).
            network_children["network_device_claim"] = {
                "data": {},
                "terraform_import_ids": [network_id],
            }

            # The module uses a bulk resource instead of individual "appliance_port"s.
            network_children["appliance_ports"] = {
                "data": {},
                # Add organization ID - any bulk resource needs it.
                "terraform_import_ids": [org_id, network_id],
            }

            # "appliance_vlan_dhcp" uses the same endpoint as "appliance_vlan"
            # and is not fetched separately by nac-collector.
            # Duplicate "appliance_vlan"s with the other resource name.
            appliance_vlans = get_list_or_empty(network_children, "appliance_vlan")
            for appliance_vlan in appliance_vlans:
                import_ids = appliance_vlan.get("terraform_import_ids", None)
                if import_ids is None:
                    continue

                network_children.setdefault("appliance_vlan_dhcp", []).append(
                    {
                        "data": {
                            "id": appliance_vlan.get("data", {}).get("id"),
                        },
                        "terraform_import_ids": import_ids,
                        # The provider has "no_import: true",
                        # so "terraform plan" with the import shows an error.
                        # The error does not mention the resource type, so the user would not be able to find the resource to remove manually.
                        # Skip and log it ahead of time instead.
                        "terraform_no_import": True,
                    }
                )

            network_group_policies = get_list_or_empty(
                network_children, "network_group_policy"
            )
            for network_group_policy in network_group_policies:
                import_ids = network_group_policy.get("terraform_import_ids", None)
                if import_ids is None:
                    continue

                # Import has an extra "force_delete" parameter in the middle -
                # a provider-only config attribute that's only used to add force=true when deleting the resource.
                # Not used in NaC (yet?).
                # Pass "false" to use the default behavior.
                import_ids.insert(1, "false")

            appliance_sdwan_internet_policies = network_children.get(
                "appliance_sdwan_internet_policies", {}
            )
            import_ids = appliance_sdwan_internet_policies.get(
                "terraform_import_ids", None
            )
            if import_ids is not None:
                # The provider has "no_import: true",
                # so "terraform plan" with the import shows an error.
                # The error does not mention the resource type, so the user would not be able to find the resource to remove manually.
                # Skip and log it ahead of time instead.
                # TODO nac-collector should take "no_import" from the provider and pass it through instead.
                appliance_sdwan_internet_policies["terraform_no_import"] = True

            devices = get_list_or_empty(network_children, "device")
            for device in devices:
                device_children = device.setdefault("children", {})
                device_serial = device.get("data", {}).get("serial")

                # Remove parent organization ID - import only takes the serial
                # (unlike "network" which does take the organization ID).
                device["terraform_import_ids"] = [device_serial]

                # The module uses a bulk resource instead of individual "switch_port"s.
                device_children["switch_ports"] = {
                    "data": {},
                    # Add organization ID - any bulk resource needs it.
                    "terraform_import_ids": [org_id, device_serial],
                }


def get_list_or_empty(dict_: dict[str, Any], key: str) -> list[Any]:
    result = dict_.get(key, [])
    if not isinstance(result, list):
        return []
    return result


def get_id_to_values(tf_file_resource, json_file_key, json_file_resource):
    """
    Process Terraform plan resources and match them with Meraki JSON data.
    Returns a dictionary mapping Terraform resource addresses to their IDs and indices.
    """
    to_dir_ = {}

    changes = [
        item
        for item in tf_file_resource
        if item
        and item.get("module_address") == "module.meraki"
        and item.get("type", "").startswith("meraki_")
    ]

    for change in changes:
        tf_resource = ".".join(
            [change.get("module_address"), change.get("type"), change.get("name")]
        )
        tf_resource_type = change.get("type")  # e.g., "meraki_wireless_ssid"
        change_index = change.get("index")

        resource = find_change_in_json(
            json_file_resource,
            change_index,
            tf_resource_type,
            json_file_key,
        )
        if resource is None:
            logger.error(
                'Failed to import Terraform change %s["%s"]: could not find it in Meraki JSON',
                tf_resource,
                change_index,
            )
            continue

        # Use terraform_import_ids added by nac-collector.
        import_ids = resource.get("terraform_import_ids")
        if import_ids is None:
            logger.error(
                'Failed to import Terraform change %s["%s"]: terraform_import_ids field is missing or None in Meraki JSON',
                tf_resource,
                change_index,
            )
            continue

        no_import = resource.get("terraform_no_import", False)
        if no_import:
            logger.error(
                'Skipping import for Terraform change %s["%s"]: the provider does not support importing this resource type ("no_import: true" in the provider definition)',
                tf_resource,
                change_index,
            )
            continue

        import_id = ",".join(str(id) for id in import_ids)
        to_dir_.setdefault(tf_resource, []).append((import_id, change_index))

    return to_dir_


def find_change_in_json(
    json_file_resource,
    change_index,
    tf_resource_type,
    json_file_key,
):
    for org_element in json_file_resource:
        if "data" not in org_element:
            continue

        org_name = org_element["data"].get("name")
        if not org_name:
            continue

        # Extract domain from change_index path
        domain = change_index.split("/")[0] if "/" in change_index else None
        if not domain:
            continue

        # Build initial path with domain and organization
        initial_path = f"{domain}/{org_name}"

        # Search for the resource starting from the top-level resource type
        # Pass expected resource type and current JSON type for validation
        resource = find_child_change_in_json(
            org_element, change_index, initial_path, tf_resource_type, json_file_key
        )
        if resource:
            return resource


def find_child_change_in_json(
    resource, target_path, current_path, expected_tf_resource_type, current_json_type
):
    """
    Recursively search for a resource matching the target path and resource type.

    Args:
        resource: Current resource dict from meraki.json
        target_path: Target path like "domain/org/network/resource"
        current_path: Current path being built during recursion
        expected_tf_resource_type: Expected Terraform resource type (e.g., "meraki_wireless_ssid")
        current_json_type: Current JSON resource type (e.g., "wireless_ssid", "network", "organization")

    Returns:
        A resource dict if found, None otherwise.
    """
    expected_json_type = tf_resource_type_to_json_type(expected_tf_resource_type)
    if current_path == target_path and expected_json_type == current_json_type:
        return resource

    # The resorce didn't match - search children for nested resources at the same path
    # Example: wireless_ssid_splash_settings is a child of wireless_ssid with the same path
    # Continue to search children below (don't return None yet)

    # If this resource doesn't match, search in children
    if "children" not in resource:
        return None

    children = resource["children"]
    if not isinstance(children, dict):
        return None

    # Iterate through all child resource types
    for child_type, child_resources in children.items():
        # Handle list of resources (most common case - e.g., multiple SSIDs)
        if isinstance(child_resources, list):
            for child_resource in child_resources:
                if "data" not in child_resource:
                    continue

                child_name = get_json_resource_key_name(child_type, child_resource)
                if not child_name:
                    # TODO The whole list of issues gets printed many times over (once for every search for a resource).
                    # Rework this log when other debug logs appear.
                    logger.debug(
                        "Skipping: Resource type '%s' at path '%s' has no 'name' field. Endpoint: %s",
                        child_type,
                        current_path,
                        child_resource.get("endpoint", "unknown"),
                    )
                    continue

                # Build path for this child resource
                child_path = f"{current_path}/{child_name}"

                # Recursively search this child, passing the JSON child type
                found_resource = find_child_change_in_json(
                    child_resource,
                    target_path,
                    child_path,
                    expected_tf_resource_type,
                    child_type,  # Pass the JSON child type (e.g., "wireless_ssid", "network")
                )
                if found_resource:
                    return found_resource

        # Handle singleton resources (dict - e.g., splash_settings, traffic_shaping_rules)
        # These are nested under their parent and share the same path
        elif isinstance(child_resources, dict) and "data" in child_resources:
            # Singleton resource at the same path as parent
            found_resource = find_child_change_in_json(
                child_resources,
                target_path,
                current_path,  # Use same path as parent
                expected_tf_resource_type,
                child_type,
            )
            if found_resource:
                return found_resource

    return None


def tf_resource_type_to_json_type(tf_resource_type):
    """
    Convert Terraform resource type to JSON resource type.

    Args:
        tf_resource_type: Terraform resource type like "meraki_wireless_ssid", "meraki_network", etc.

    Returns:
        JSON resource type like "wireless_ssid", "network", etc.

    Examples:
    - "meraki_network" -> "network"
    - "meraki_wireless_ssid_splash_settings" -> "wireless_ssid_splash_settings"
    """

    # Remove "meraki_" prefix from the resource type to match nac-collector's types
    # (which are taken from provider definition filenames which don't have the prefix)
    if tf_resource_type.startswith("meraki_"):
        return tf_resource_type[len("meraki_") :]

    # Note that the prefix is not removed if it is missing (possibly a non-meraki-provider resource)
    # but those changes are skipped, so it should not happen here.
    return tf_resource_type


def get_json_resource_key_name(json_resource_type, json_resource):
    """
    Get the last element of the Terraform key for the resource from the JSON.
    Examples:
    - "network" (key = "domain/org/net") -> "net"
    - "appliance_vlan" (key = "domain/org/net/12") -> 12
    - "switch_qos_rule" (key = "domain/org/net/400212121212121212") -> "400212121212121212"
      (ID used as the name by nac-tool since the API has no name field to import)
    """

    # TODO Have this in a common place to be shared with nac-tool / terraform-generator / robogen?
    custom_key_fields = {
        # The module uses "vlan_id" even though both the schema and the API have a "name" (which is also required in the API).
        # "vlan_id" in the schema, "id" in the API.
        "appliance_vlan": "id",
        "appliance_vlan_dhcp": "id",
        # "service_name" in the schema, "service" in the API.
        "appliance_firewalled_service": "service",
        # "name" in the schema, nothing in the API - nac-tool uses "adaptivePolicyId" as "name" instead.
        "organization_adaptive_policy": "adaptivePolicyId",
        # "short_name" in the schema, "shortName" in the API.
        "organization_early_access_features_opt_in": "shortName",
        # "trusted_server_name" in the schema, nothing in the API - nac-tool uses "trustedServerId" as "trusted_server_name" instead.
        "switch_dhcp_server_policy_arp_inspection_trusted_server": "trustedServerId",
        # "link_aggregation_name" in the schema, nothing in the API - nac-tool uses "id" as "link_aggregation_name" instead.
        "switch_link_aggregation": "id",
        # "qos_rule_name" in the schema, nothing in the API - nac-tool uses "id" as "qos_rule_name" instead.
        "switch_qos_rule": "id",
        # "rendezvous_point_name" in the schema, nothing in the API - nac-tool uses "rendezvousPointId" as "rendezvous_point_name" instead.
        "switch_routing_multicast_rendezvous_point": "rendezvousPointId",
    }

    key_field = custom_key_fields.get(json_resource_type, "name")
    return json_resource["data"].get(key_field)


def tf_import(meraki_json_path: Path):
    logger.info("Starting Terraform import generation...")
    # cleanup old files
    logger.info("Cleaning up old import files...")
    IMPORT_TF_PATH.unlink(missing_ok=True)

    logger.info("Loading Meraki JSON data from %s...", meraki_json_path)
    meraki_json = None
    with open(meraki_json_path) as file:
        meraki_json = json.load(file)

    logger.info("Preprocessing Meraki JSON data...")
    preprocess_json(meraki_json)

    logger.info("Initializing Terraform...")
    subprocess.run(["terraform", "init"], cwd=CWD, check=True)

    logger.info("Generating Terraform plan...")
    subprocess.run(
        ["terraform", "plan", "-out=" + IMPORT_PLAN_FILENAME, "-input=false"],
        cwd=CWD,
        check=True,
    )
    logger.info("Saving plan json to %s", IMPORT_PLAN_JSON_PATH)
    with open(IMPORT_PLAN_JSON_PATH, "w") as f:
        subprocess.run(
            ["terraform", "show", "-json", IMPORT_PLAN_FILENAME],
            stdout=f,
            cwd=CWD,
            check=True,
        )

    tf_plan = None
    with open(IMPORT_PLAN_JSON_PATH) as file:
        tf_plan = json.load(file)
    logger.info(
        "Loaded %s resources from Terraform plan",
        len(tf_plan.get("resource_changes", [])),
    )

    logger.info(
        "Generating %s from %s and Terraform plan", IMPORT_TF_PATH, meraki_json_path
    )

    to_dir_ = {}
    for json_file_key, json_file_resource in meraki_json.items():
        tf_file_resource = tf_plan.get("resource_changes", [])
        result = get_id_to_values(tf_file_resource, json_file_key, json_file_resource)
        # Merge results into to_dir_
        for key, values in result.items():
            to_dir_.setdefault(key, []).extend(values)

    logger.info(
        "Found %s resources to import into Terraform state",
        sum(len(v) for v in to_dir_.values()),
    )
    terraform_imports = ""
    for tf_resource, instances in to_dir_.items():
        for id, index in instances:
            terraform_imports += "import {\n"
            terraform_imports += f'  id = "{id}"\n'
            if isinstance(index, int):
                terraform_imports += f"  to = {tf_resource}[{index}]\n"
            else:
                terraform_imports += f'  to = {tf_resource}["{index}"]\n'
            terraform_imports += "}\n"
    logger.info("Writing import statements to %s", IMPORT_TF_PATH)
    with open(IMPORT_TF_PATH, "w") as file:
        file.write(terraform_imports)

    # cleanup
    logger.info("Cleaning up temporary files...")
    IMPORT_PLAN_PATH.unlink(missing_ok=True)
    IMPORT_PLAN_JSON_PATH.unlink(missing_ok=True)


def print_usage() -> None:
    print("""\
Usage: import.py /path/to/meraki.json

Prerequisites:
- meraki.json fetched via nac-collector;
- a Terraform main.tf in the current directory pointing to .nac.yaml files obtained from meraki.json via nac-tool.
""")


if __name__ == "__main__":
    try:
        meraki_json_path = Path(sys.argv[1])
    except IndexError:
        print_usage()
        exit(1)
    logging.basicConfig(level=logging.INFO)
    tf_import(meraki_json_path)
