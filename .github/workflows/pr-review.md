---
on:
  pull_request:
    types: [opened, synchronize, closed]
permissions:
      contents: read
      issues: read
      pull-requests: read
engine: copilot
model: gpt-4.1
network:
  allowed:
    - defaults
    - python
    - "github.com"
tools:
  github:
    toolsets: [default]
safe-outputs:
  add-comment:
    max: 1
  add-labels:
  add-reviewer:
  assign-to-agent:
  assign-to-user:
  close-pull-request:
  create-pull-request-review-comment:
    max: 10
  hide-comment:
  link-sub-issue:
  submit-pull-request-review:
    allowed-events: [COMMENT]
  remove-labels:
  reply-to-pull-request-review-comment:
  report-failure-as-issue: false
  resolve-pull-request-review-thread:
  unassign-from-user:
  update-issue:
  update-pull-request:
---

# pr-review

For an opened or updated pull request, review the changes against the provided
description and leave inline comments as necessary. Once the pull request is
updated, repeat the review.

When a pull request is closed, act only if it was merged. Identify every GitHub
issue explicitly addressed by the merged pull request (including `Closes`,
`Fixes`, and equivalent references, plus the issue body and changed files).
Compare each issue's acceptance criteria with the implementation on the merged
default branch. Close an issue with a concise comment linking the merged pull
request only when the implementation is complete and the pull request is
actually merged. Do not close issues for documentation-only planning,
references, open or closed-unmerged pull requests, or partial implementations.
If an issue is only partially addressed, leave it open and explain the
remaining work in a comment.

When planning or implementing work for multiple issues, keep each issue in a
separate pull request whenever the changes can be reasonably separated. A pull
request may combine issues only when they share one cohesive implementation;
list every included issue and its acceptance-criteria evidence in the
description. Never close an issue merely because a pull request mentions it.

Finalise review by leaving a summary comment with all the findings and recommendations, or just leave - LGTM if no major concerns.

During review it's important to check readability of the code:
- clear variable and method names
- logical and easy to follow structure of the files

It's important to make sure logs are added to the critical decision points,
and the right logging level (INFO, WARN, ERROR) is used, depending on the severity and type of the logged message.

Ensure that there is decent error handling in place - code should be robust and resilient.

Ensure there are no security concerns - user input is validated, properly escaped, and not used in the raw SQL expressions.

<!--
## TODO: Customize this workflow

The workflow has been generated based on your selections. Consider adding:

- [ ] More specific instructions for the AI
- [ ] Error handling requirements
- [ ] Output format specifications
- [ ] Integration with other workflows
- [ ] Testing and validation steps

## Configuration Summary

- **Trigger**: Pull request opened or synchronized
- **AI Engine**: copilot
- **Tools**: github
- **Safe Outputs**: close-pull-request, add-comment, create-pull-request-review-comment, submit-pull-request-review, reply-to-pull-request-review-comment, resolve-pull-request-review-thread, add-labels, remove-labels, add-reviewer, assign-to-agent, assign-to-user, unassign-from-user, update-issue, update-pull-request, link-sub-issue, hide-comment
- **Network Access**: defaults,python

## Next Steps

1. Review and customize the workflow content above
2. Remove TODO sections when ready
3. Run `gh aw compile` to generate the GitHub Actions workflow
4. Test the workflow with a manual trigger or appropriate event
-->
