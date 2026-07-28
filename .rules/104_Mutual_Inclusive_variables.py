import jmespath


class Rule:
    id = "104"
    description = "Verify if any mutually dependent variables are defined"
    severity = "HIGH"

    #########################################################################################################################################
    # List of mutually inclusive variable pairs in the Meraki Data Model.
    # For each entry, if any variable in trigger_vars is defined, all variables in required_vars must also be defined.
    # Add entries here as needed — no code changes required.
    #
    # Fields:
    # 1. object_jmes_path: JMESPath to the flattened object list to check.
    #       example: "meraki.domains[].organizations[].networks[].devices[].switch.ports[].port_id_ranges[]"
    # 2. trigger_vars: List of variables — if any one of them is defined, all required_vars must also be defined.
    #       example: ['slot', 'module']
    # 3. required_vars: Variables that must all be defined whenever any trigger_var is present.
    #       example: ['slot', 'module']
    #########################################################################################################################################

    mutually_inclusive_variables_list = [
        # slot and module are mutually inclusive on port_id_ranges entries for modular switch expansion ports.
        # If either is defined, both must be defined.
        {
            "object_jmes_path": "meraki.domains[].organizations[].networks[].devices[].switch.ports[].port_id_ranges[]",
            "trigger_vars": ["slot", "module"],
            "required_vars": ["slot", "module"],
        },
    ]

    @classmethod
    def match(cls, inventory):
        results = []
        for each_inclusion_item in cls.mutually_inclusive_variables_list:
            data_model_path = each_inclusion_item.get("object_jmes_path")
            try:
                data = jmespath.search(
                    each_inclusion_item.get("object_jmes_path"), inventory
                )
                if data is not None:
                    if isinstance(data, dict):
                        data = [data]
                    for each_data in data:
                        trigger_vars = each_inclusion_item.get("trigger_vars")
                        triggered = any(
                            jmespath.search(t, each_data) is not None
                            for t in trigger_vars
                        )
                        if triggered:
                            for required_var in each_inclusion_item.get(
                                "required_vars"
                            ):
                                required_data = jmespath.search(required_var, each_data)
                                if required_data is None:
                                    results.append(
                                        "On Data model path "
                                        + data_model_path
                                        + ", one of "
                                        + str(trigger_vars)
                                        + " is defined, but the required variable '"
                                        + required_var
                                        + "' is not defined."
                                    )
            except KeyError:
                pass
        return results
