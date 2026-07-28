from pathlib import Path

VALID_TIMEZONES_FILE = "valid_timezones.txt"
script_dir = Path(__file__).parent
VALID_TIMEZONES_PATH = script_dir / VALID_TIMEZONES_FILE


# Uncomment the following code if you want to generate the
# valid_timezones.txt file
# using zoneinfo module in python.
# zoneinfo is a standard library module in Python 3.9 and later

# import zoneinfo
# valid_timezones_data_create = zoneinfo.available_timezones()
# # write new zoneinfo.available_timezones to file
# with open(VALID_TIMEZONES_PATH, "w") as f:
#     f.write("\n".join(valid_timezones_data_create))


class Rule:
    id = "301"
    description = "Check for timezone provided matches valid timezones"
    severity = "HIGH"

    # full_path = "meraki.domains.organizations.networks.time_zone"

    # traverse the inventory and return a list of {full_path: time_zone}
    # full_path - meraki.domains[0].organizations[0].networks[0].time_zone
    # where domains, organizations, networks are lists of objects
    # time_zone contains a string with the timezone name
    @classmethod
    def identify_time_zones_defined(cls, inventory_full):
        time_zones_defined = []
        inventory = inventory_full.get("meraki", {})
        for do_index, domain in enumerate(inventory.get("domains", [])):
            for o_index, organization in enumerate(domain.get("organizations", [])):
                for n_index, network in enumerate(organization.get("networks", [])):
                    net_time_zone = network.get("time_zone")
                    if net_time_zone:
                        time_zones_defined.append(
                            {
                                "full_path": f"domains[{do_index}].organizations[{o_index}].networks[{n_index}].time_zone",
                                "time_zone": net_time_zone,
                            }
                        )
        return time_zones_defined

    @classmethod
    def check_time_zone(cls, net_time_zones, valid_timezones):
        results = []
        # Check if the timezone is valid
        for net_time_zone in net_time_zones:
            if net_time_zone["time_zone"] not in valid_timezones:
                results.append(
                    {
                        "path": net_time_zone["full_path"],
                        "message": f"Invalid timezone: {net_time_zone['time_zone']}",
                    }
                )
        return results

    @classmethod
    def match(cls, inventory):
        results = []
        if VALID_TIMEZONES_PATH.exists() and VALID_TIMEZONES_PATH.is_file():
            with open(VALID_TIMEZONES_PATH, "r") as f:
                valid_timezones = set(f.read().splitlines())
        else:
            # valid timezones file not found
            results.append(
                {
                    "path": VALID_TIMEZONES_PATH,
                    "message": f"Valid timezones file not found: {VALID_TIMEZONES_PATH}",
                }
            )
            return results

        if not valid_timezones:
            # if valid timezones file is empty return error
            results.append(
                {
                    "path": VALID_TIMEZONES_PATH,
                    "message": f"Valid timezones file is empty: {VALID_TIMEZONES_PATH}",
                }
            )
            return results
            # Check if the timezone is valid
        net_time_zones = cls.identify_time_zones_defined(inventory)
        results = cls.check_time_zone(net_time_zones, valid_timezones)

        return results
