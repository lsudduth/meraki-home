import json


class Rule:
    id = "201"
    description = "Check for claimed devices"
    severity = "HIGH"

    # full_path = "meraki.domains.organizations.networks.devices.serial"

    @classmethod
    # traverse the inventory and return a list of {full_path: serial}
    # full_path - meraki.domains[0].organizations[0].networks[0].devices[0].serial
    # where domains, organizations, networks, devices are lists of objects
    # serials contains a list of {full_path: serial}
    def extract_serials(cls, inventory):
        serials = []
        for do_index, domain in enumerate(inventory.get("domains", [])):
            for o_index, organization in enumerate(domain.get("organizations", [])):
                for n_index, network in enumerate(organization.get("networks", [])):
                    for de_index, device in enumerate(network.get("devices", [])):
                        serials.append(
                            {
                                "full_path": f"domains[{do_index}].organizations[{o_index}].networks[{n_index}].devices[{de_index}].serial",
                                "serial": device.get("serial"),
                            }
                        )
        return serials

    # return a list of claimed serials from the terraform statefile
    @classmethod
    def get_claimed_serials(cls, statefile):
        claimed_serials = []
        with open(statefile, "r") as f:
            state = json.load(f)
            for resource in state.get("resources", []):
                if resource.get("type") == "meraki_device":
                    claimed_serials.append(
                        resource.get("instances", [{}])[0]
                        .get("attributes", {})
                        .get("serial")
                    )
        return claimed_serials

    # check if the serial is claimed in the dashboard
    @classmethod
    def claim_check(cls, inventory, serials):
        results = []
        claimed_serials = cls.get_claimed_serials("terraform.tfstate")
        for serial in serials:
            if serial in claimed_serials:
                results.append({"serial": serial, "claimed": True})
            else:
                results.append({"serial": serial, "claimed": False})

        return results

    @classmethod
    def match(cls, inventory):
        results = []
        # Commented out as placeholder
        # serials = cls.extract_serials(inventory)
        # results = cls.claim_check(inventory, serials)
        return results
