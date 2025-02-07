#!/usr/bin/env python

# Output the issues fixed in a particular JIRA release.
# Can be used with any JIRA project but defaults to SYNPY.

# Examples:
# # output release issues in rst format
# print_release_issues.py py-2.4 rst

# # output release issues for SYNR synapser-0.10 github
# print_release_issues.py --project SYNR synapser-0.10 github


import argparse
import collections
import json
import base64
import sys
import httpx

JQL_ISSUE_URL = "https://sagebionetworks.jira.com/rest/api/2/search?jql=project={project}%20AND%20fixVersion={version}%20ORDER%20BY%20created%20ASC&startAt={start_at}"  # noqa
ISSUE_URL_PREFIX = "https://sagebionetworks.jira.com/browse/{key}"

RST_ISSUE_FORMAT = """-  [`{key} <{url}>`__] -
   {summary}"""
GITHUB_ISSUE_FORMAT = "-  \\[[{key}]({url})\\] - {summary}"
MARKDOWN_FORMAT = "-  \\[[{key}]({url})\\] - {summary}"


def _get_issues(project, version):
    start_at = 0
    issues_by_type = {}
    client = httpx.Client()
    while True:
        url = JQL_ISSUE_URL.format(
            project=project,
            version=version,
            start_at=start_at,
        )
        # In order to use this script you need to create an API token
        # Follow the link below and create a token - DO NOT COMMIT YOUR TOKEN TO VCS
        # https://id.atlassian.com/manage-profile/security/api-tokens
        # Use the following format for the token
        # `username:token`, ie: `first.last@sagebase.org:token`
        sample_string_bytes = "".encode("ascii")
        if not sample_string_bytes:
            raise RuntimeError(
                "As of May 2024 you must authenticate in order to query jira. See the comments in the script for more information."
            )

        basic_auth = base64.b64encode(sample_string_bytes).decode("ASCII")

        client.headers["Authorization"] = f"Basic {basic_auth}"
        response = client.get(url=url)
        response_json = json.loads(response.read())

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to get issues from JIRA: {response.status_code} {response.text}"
            )

        issues = response_json["issues"]
        if not issues:
            break

        for issue in issues:
            issue_type = issue["fields"]["issuetype"]["name"]
            issues_for_type = issues_by_type.setdefault(issue_type, [])
            issues_for_type.append(issue)

        start_at += len(issues)

    issue_types = sorted(issues_by_type)
    issues_by_type_ordered = collections.OrderedDict()
    for issue_type in issue_types:
        issues_by_type_ordered[issue_type] = issues_by_type[issue_type]

    return issues_by_type_ordered


def _pluralize_issue_type(issue_type, format_type: str):
    if issue_type == "Bug":
        title = "Bug Fixes"
        if format_type == "md":
            return f"### {title}"
        return title
    elif issue_type == "Story":
        title = "Stories"
        if format_type == "md":
            return f"### {title}"
        return title

    title = issue_type + "s"
    if format_type == "md":
        return f"### {title}"
    return title


def print_issues(issues_by_type, issue_format, format_type: str, file=sys.stdout):
    for issue_type, issues in issues_by_type.items():
        issue_type_plural = _pluralize_issue_type(
            issue_type=issue_type, format_type=format_type
        )
        print(issue_type_plural, file=file)
        if format_type != "md":
            print("-" * len(issue_type_plural), file=file)

        for issue in issues:
            issue_key = issue["key"]
            issue_url = ISSUE_URL_PREFIX.format(key=issue_key)
            issue_summary = issue["fields"]["summary"]
            print(
                issue_format.format(
                    key=issue_key, url=issue_url, summary=issue_summary
                ),
                file=file,
            )

        # newline
        print(file=file)


def main():
    """Builds the argument parser and returns the result."""

    parser = argparse.ArgumentParser(
        description="Generates release note issue list in desired format"
    )

    parser.add_argument(
        "version",
        help="The JIRA release version whose issues will be included in the release notes",
    )
    parser.add_argument(
        "format", help="The output format", choices=["github", "rst", "md"]
    )
    parser.add_argument("--project", help="The JIRA project", default="SYNPY")

    args = parser.parse_args()
    issues = _get_issues(args.project, args.version)
    if args.format == "md":
        issue_format = MARKDOWN_FORMAT
    elif args.format == "rst":
        issue_format = RST_ISSUE_FORMAT
    else:
        issue_format = GITHUB_ISSUE_FORMAT
    print_issues(
        issues_by_type=issues, issue_format=issue_format, format_type=args.format
    )


if __name__ == "__main__":
    main()
