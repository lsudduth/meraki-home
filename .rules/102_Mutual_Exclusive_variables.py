import jmespath


class Rule:
    id = "102"
    description = "Verify if any mutually exclusive variables are defined"
    severity = "HIGH"

    #########################################################################################################################################
    # Generic rule for validating mutually exclusive variables in any configuration
    #
    # This rule uses JMESPath to dynamically navigate to target objects and check if mutually exclusive
    # variables are configured together. It works with any hierarchical data model.
    #
    # Configuration structure:
    #   object_jmes_path: JMESPath expression to locate target objects
    #                     Example: 'meraki.domains[].organizations[].networks[].devices[].management_interface'
    #   variable1_jmes_path: Optional JMESPath to navigate further within target object (empty = use target directly)
    #   variable1: List of variable names in the first group
    #   variable2_jmes_path: Optional JMESPath to navigate further within target object (empty = use target directly)
    #   variable2: List of variable names in the second group (mutually exclusive with variable1)
    #
    # Validation logic:
    #   1. Use object_jmes_path to locate all target objects
    #   2. Optionally navigate further using variable1_jmes_path and variable2_jmes_path
    #   3. Check if any variable from variable1 list AND any variable from variable2 list both exist
    #   4. Report violation with full hierarchical context path
    #
    # Example configuration (Meraki device management interfaces):
    #   devices:
    #     - name: ap_01
    #       management_interface:
    #         lan_ip:              # LAN mode configured
    #           using_static_ip: true
    #           static_ip: 192.168.10.101
    #         wan1:                # WAN mode also configured - VIOLATION!
    #           using_static_ip: true
    #           vlan: 10
    #
    # The rule is fully dynamic and can be reused for any mutually exclusive validation scenario
    # by adding entries to the mutually_exclusive_variables_list below.
    #########################################################################################################################################

    mutually_exclusive_variables_list = [
        # Meraki device management interface: WAN vs LAN modes
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].devices[].management_interface",
            "variable1_jmes_path": "",
            "variable1": ["wan1", "wan2"],
            "variable2_jmes_path": "",
            "variable2": ["lan_ip"],
        },
        # Add additional mutually exclusive variable checks here as needed
        # Example:
        # {
        #     'object_jmes_path': 'meraki.domains[].organizations[].networks[].wireless.ssids[]',
        #     'variable1_jmes_path' : 'authentication',
        #     'variable1' : ['psk', 'open'],
        #     'variable2_jmes_path' : 'authentication',
        #     'variable2' : ['radius'],
        # },
        # Firmware: a product cannot appear in both upgrade and downgrade for the same network
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].firmware",
            "variable1_jmes_path": "upgrade.products",
            "variable1": ["switch"],
            "variable2_jmes_path": "downgrade.products",
            "variable2": ["switch"],
            "error_message": "firmware: 'switch' cannot be in both upgrade and downgrade.",
        },
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].firmware",
            "variable1_jmes_path": "upgrade.products",
            "variable1": ["switch_catalyst"],
            "variable2_jmes_path": "downgrade.products",
            "variable2": ["switch_catalyst"],
            "error_message": "firmware: 'switch_catalyst' cannot be in both upgrade and downgrade.",
        },
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].firmware",
            "variable1_jmes_path": "upgrade.products",
            "variable1": ["wireless"],
            "variable2_jmes_path": "downgrade.products",
            "variable2": ["wireless"],
            "error_message": "firmware: 'wireless' cannot be in both upgrade and downgrade.",
        },
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].firmware",
            "variable1_jmes_path": "upgrade.products",
            "variable1": ["appliance"],
            "variable2_jmes_path": "downgrade.products",
            "variable2": ["appliance"],
            "error_message": "firmware: 'appliance' cannot be in both upgrade and downgrade.",
        },
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].firmware",
            "variable1_jmes_path": "upgrade.products",
            "variable1": ["cellular_gateway"],
            "variable2_jmes_path": "downgrade.products",
            "variable2": ["cellular_gateway"],
            "error_message": "firmware: 'cellular_gateway' cannot be in both upgrade and downgrade.",
        },
    ]

    @classmethod
    def get_hierarchy_context(cls, inventory, base_jmespath):
        """
        Build a mapping of target objects to their hierarchical context for better error reporting.
        Fully dynamic implementation that works with any JMESPath hierarchy.

        Args:
            inventory: The data inventory
            base_jmespath: The JMESPath query (e.g., 'meraki.domains[].organizations[].networks[].devices[].management_interface')

        Returns: dict mapping id(target_object) -> context info with all hierarchy levels
        """
        context_map = {}

        try:
            # Parse the jmespath path to extract hierarchy levels
            # Example: 'meraki.domains[].organizations[].networks[].devices[].management_interface'
            # Becomes: ['meraki', 'domains', 'organizations', 'networks', 'devices', 'management_interface']
            path_parts = base_jmespath.replace("[]", "").split(".")

            if len(path_parts) < 2:
                return context_map

            # Recursive function to traverse the hierarchy dynamically
            def traverse_hierarchy(data, path_index, context, context_order):
                """
                Recursively traverse the data structure following the path_parts.

                Args:
                    data: Current data object being traversed
                    path_index: Current index in path_parts
                    context: Dictionary containing names of parent objects at each level
                    context_order: List maintaining the order of context keys as encountered
                """
                # Base case: reached the target object
                if path_index >= len(path_parts):
                    return

                current_key = path_parts[path_index]

                # If we're at the last part, this is the target object
                if path_index == len(path_parts) - 1:
                    if isinstance(data, dict):
                        target_obj = data.get(current_key)
                        if target_obj:
                            context_map[id(target_obj)] = {
                                "context": context.copy(),
                                "order": context_order.copy(),
                            }
                    return

                # Get the next level data
                if isinstance(data, dict):
                    next_data = data.get(current_key)
                else:
                    return

                # If next_data is a list, iterate through items
                if isinstance(next_data, list):
                    for item in next_data:
                        # Create a new context with the current item's name
                        new_context = context.copy()
                        new_order = context_order.copy()
                        item_name = (
                            item.get("name", "unknown")
                            if isinstance(item, dict)
                            else "unknown"
                        )
                        context_key = f"{current_key}_name"
                        new_context[context_key] = item_name
                        new_order.append(context_key)

                        # Recursively traverse deeper
                        traverse_hierarchy(item, path_index + 1, new_context, new_order)

                # If next_data is a dict, continue traversing
                elif isinstance(next_data, dict):
                    new_context = context.copy()
                    new_order = context_order.copy()
                    traverse_hierarchy(
                        next_data, path_index + 1, new_context, new_order
                    )

            # Start traversal from the root
            root_key = path_parts[0]
            root_data = inventory.get(root_key, {})
            traverse_hierarchy(root_data, 1, {}, [])

        except (KeyError, TypeError, AttributeError, IndexError):
            pass

        return context_map

    @classmethod
    def match(cls, inventory):
        results = []

        # Loop through the mutually_exclusive_variables_list
        for each_exclusion_item in cls.mutually_exclusive_variables_list:
            try:
                # Step 1: Use JMESPath to narrow down to the target dictionaries (e.g., management_interface objects)
                object_jmes_path = each_exclusion_item.get("object_jmes_path", "*")
                target_objects = jmespath.search(object_jmes_path, inventory)

                if target_objects is None:
                    continue

                # Normalize data to a list for consistent processing
                if isinstance(target_objects, dict):
                    # Single object returned (e.g., JMESPath without [] flatten operators)
                    target_objects = [target_objects]
                elif isinstance(target_objects, list):
                    # List returned (e.g., JMESPath with [] flatten operators) - use as-is
                    pass  # Already a list
                else:
                    # Unexpected type (string, int, etc.) - skip processing
                    continue

                # Build hierarchy context dynamically for better error messages
                context_map = cls.get_hierarchy_context(inventory, object_jmes_path)

                # Step 2: Check each target object (e.g., each management_interface)
                for target_obj in target_objects:
                    if target_obj is None:
                        continue

                    # Step 3: Navigate further with variable1_jmes_path if specified
                    variable1_jmes_path = each_exclusion_item.get(
                        "variable1_jmes_path", ""
                    )
                    if variable1_jmes_path:
                        # Further narrow down using JMESPath
                        var1_data = jmespath.search(variable1_jmes_path, target_obj)
                    else:
                        # Use the target object directly
                        var1_data = target_obj

                    # Step 4: Navigate further with variable2_jmes_path if specified
                    variable2_jmes_path = each_exclusion_item.get(
                        "variable2_jmes_path", ""
                    )
                    if variable2_jmes_path:
                        # Further narrow down using JMESPath
                        var2_data = jmespath.search(variable2_jmes_path, target_obj)
                    else:
                        # Use the target object directly
                        var2_data = target_obj

                    # Step 5: Check if both var1_data and var2_data exist
                    if var1_data is None or var2_data is None:
                        continue

                    # Step 6: Use .get() method to check for presence of mutually exclusive variables
                    variable1_list = each_exclusion_item.get("variable1", [])
                    variable2_list = each_exclusion_item.get("variable2", [])

                    # Check each combination of variable1 with variable2
                    for var1_name in variable1_list:
                        var1_value = var1_data.get(var1_name)

                        for var2_name in variable2_list:
                            var2_value = var2_data.get(var2_name)

                            # Step 7: If both variables exist (are not None), report violation
                            if var1_value is not None and var2_value is not None:
                                # Get hierarchy context for better error messages (fully dynamic)
                                context_data = context_map.get(id(target_obj), {})

                                # Build a dynamic hierarchical path from all available context
                                # Example: "domain_name > org_name > network_name > device_name"
                                if (
                                    context_data
                                    and "context" in context_data
                                    and "order" in context_data
                                ):
                                    context = context_data["context"]
                                    order = context_data["order"]
                                    # Use the order to build the hierarchy path in the correct sequence
                                    # Convert values to strings to handle TaggedScalar objects from ruamel.yaml
                                    hierarchy_path = " > ".join(
                                        [
                                            str(context[key])
                                            for key in order
                                            if key in context
                                        ]
                                    )
                                    location_msg = f"at {hierarchy_path}"
                                else:
                                    location_msg = "at unknown location"

                                results.append(
                                    each_exclusion_item["error_message"].rstrip(".")
                                    + f" {location_msg}"
                                    if "error_message" in each_exclusion_item
                                    else (
                                        f"Mutually exclusive variables detected {location_msg}: "
                                        f"'{var1_name}' is defined in both "
                                        f"'{variable1_jmes_path}' and '{variable2_jmes_path}'. "
                                        f"Only one should be configured."
                                    )
                                )

            except (KeyError, TypeError, AttributeError):
                # Skip processing if there's an error accessing the data structure
                pass

        return results
