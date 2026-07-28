# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Daniel Schmidt <danischm@cisco.com>

# Expects the following environment variables:
# - WEBEX_TOKEN
# - WEBEX_ROOM_ID
# - JOB_NAME
# - BUILD_DISPLAY_NAME
# - RUN_DISPLAY_URL
# - BUILD_URL
# - GIT_COMMIT_MESSAGE
# - GIT_URL
# - GIT_COMMIT_AUTHOR
# - GIT_BRANCH
# - GIT_EVENT
# - BUILD_STATUS

import json
import os
import requests

TEMPLATE = """[**[{status}] {job_name} {build}**]({url})
* _Commit_: [{commit}]({git_url})
* _Author_: {author}
* _Branch_: {branch}
* _Event_: {event}
""".format(
    status=str(os.getenv("BUILD_STATUS") or "").lower(),
    job_name=str(os.getenv("JOB_NAME")).rsplit("/", 1)[0],
    build=os.getenv("BUILD_DISPLAY_NAME"),
    url=os.getenv("RUN_DISPLAY_URL"),
    commit=os.getenv("GIT_COMMIT_MESSAGE"),
    git_url=os.getenv("GIT_URL"),
    author=os.getenv("GIT_COMMIT_AUTHOR"),
    branch=os.getenv("GIT_BRANCH"),
    event=os.getenv("GIT_EVENT"),
)

FMT_OUTPUT = """\n**Terraform FMT Errors**
```
"""

VALIDATE_OUTPUT = """\n**Validate Errors**
```
"""

PLAN_OUTPUT = """\n[**Terraform Plan**]({})
```
""".format(
    os.getenv("RUN_ARTIFACTS_DISPLAY_URL")
)

TEST_OUTPUT = """\n[**Testing**]({}artifact/tests/results/meraki/log.html)
```
""".format(
    os.getenv("BUILD_URL")
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
