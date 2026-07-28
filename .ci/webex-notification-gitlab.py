# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Daniel Schmidt <danischm@cisco.com>

# Expects the following environment variables:
# - WEBEX_TOKEN
# - WEBEX_ROOM_ID
# - CI_PROJECT_ROOT_NAMESPACE
# - CI_PROJECT_NAME
# - CI_PIPELINE_ID
# - CI_PIPELINE_URL
# - CI_COMMIT_TITLE
# - CI_PROJECT_URL
# - CI_COMMIT_SHA
# - GITLAB_USER_NAME
# - CI_BUILD_REF_NAME
# - CI_PIPELINE_SOURCE
# - CI_JOB_URL

import json
import os
import requests
import sys


TEMPLATE = """[**[{status}] {namespace_name}/{title} #{pipeline_id}**]({url})
* _Commit_: [{commit}]({git_url})
* _Author_: {author}
* _Branch_: {branch}
* _Event_: {event}
""".format(
    status="success" if sys.argv[1] == "-s" else "failure",
    namespace_name=str(os.getenv("CI_PROJECT_ROOT_NAMESPACE")),
    title=os.getenv("CI_PROJECT_NAME"),
    pipeline_id=os.getenv("CI_PIPELINE_ID"),
    url=os.getenv("CI_PIPELINE_URL"),
    commit=os.getenv("CI_COMMIT_TITLE"),
    git_url=f"{os.getenv('CI_PROJECT_URL')}/commit/{os.getenv('CI_COMMIT_SHA')}",
    author=os.getenv("GITLAB_USER_NAME"),
    branch=os.getenv("CI_BUILD_REF_NAME"),
    event=os.getenv("CI_PIPELINE_SOURCE"),
)

FMT_OUTPUT = """\n**Terraform FMT Errors**
```
"""

VALIDATE_OUTPUT = """\n**Validate Errors**
```
"""

PLAN_OUTPUT = """\n[**Terraform Plan**]({}/artifacts/raw/plan.txt)
```
""".format(
    os.getenv("CI_JOB_URL")
)

TEST_OUTPUT = """\n[**Testing**]({}/artifacts/raw/tests/results/meraki/report.html)
```
""".format(
    os.getenv("CI_JOB_URL")
)


def main():
    message = TEMPLATE
    if os.path.isfile("./fmt_output.txt"):
        with open("./fmt_output.txt", "r") as fmt_file:
            fmt_output = fmt_file.read()
            if len(fmt_output.strip()):
                message += FMT_OUTPUT + fmt_output + "\n```\n"
    if os.path.isfile("./validate_output.txt"):
        with open("./validate_output.txt", "r") as validate_file:
            validate_output = validate_file.read()
            if len(validate_output.strip()):
                message += VALIDATE_OUTPUT + validate_output + "\n```\n"
    if os.path.isfile("./plan.txt"):
        with open("./plan.txt", "r") as in_file:
            plan = in_file.read()
        for line in plan.split("\n"):
            if line.startswith("Plan:"):
                message += PLAN_OUTPUT + line[6:-1] + "\n```\n"
    if os.path.isfile("./test_output.txt"):
        with open("./test_output.txt", "r") as in_file:
            tests = in_file.read()
        tests_line = ""
        for line in tests.split("\n"):
            if "tests, " in line:
                tests_line = line
        if tests_line:
            message += TEST_OUTPUT + tests_line[0:-1] + "\n```\n"

    body = {"roomId": os.getenv("WEBEX_ROOM_ID"), "markdown": message}
    headers = {
        "Authorization": "Bearer {}".format(os.getenv("WEBEX_TOKEN")),
        "Content-Type": "application/json",
    }
    resp = requests.post(
        "https://api.ciscospark.com/v1/messages", headers=headers, data=json.dumps(body)
    )
    if resp.status_code != 200:
        print(
            "Webex notification failed, status code: {}, response: {}.".format(
                resp.status_code, resp.text
            )
        )


if __name__ == "__main__":
    main()
