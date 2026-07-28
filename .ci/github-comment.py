# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Daniel Schmidt <danischm@cisco.com>

# Expects the following environment variables:
# - GITHUB_TOKEN
# - REPO
# - CHANGE_ID

import json
import os
import requests
import sys

GITHUB_API_URL = "https://wwwin-github.cisco.com/api/v3/repos"


def main():
    if os.getenv("CHANGE_ID") in ["", None]:
        return
    with open("./plan.txt", "r") as in_file:
        plan = in_file.read()
    message = "<details><summary>Terraform Plan</summary>\n\n```terraform\n"
    message += plan
    message += "\n```\n</details>\n"

    body = {"body": message}
    headers = {"Authorization": "token {}".format(os.getenv("GITHUB_TOKEN"))}
    url = "{}/{}/issues/{}/comments".format(
        GITHUB_API_URL, os.getenv("REPO"), os.getenv("CHANGE_ID")
    )
    resp = requests.post(
        url,
        headers=headers,
        data=json.dumps(body),
    )
    if resp.status_code not in [200, 201]:
        print(
            "Adding GitHub comment failed, status code: {}, response: {}.".format(
                resp.status_code, resp.text
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
