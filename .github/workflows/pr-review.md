---
on:
  pull_request:
    types: [opened, synchronize]
permissions:
      contents: read
      issues: read
      pull-requests: read
engine: copilot
network:
  allowed:
    - defaults
    - python
tools:
  github:
    toolsets: [default]
safe-outputs:
  close-pull-request:
  add-comment:
  create-pull-request-review-comment:
  submit-pull-request-review:
  reply-to-pull-request-review-comment:
  resolve-pull-request-review-thread:
  add-labels:
  remove-labels:
  add-reviewer:
  assign-to-agent:
  assign-to-user:
  unassign-from-user:
  update-issue:
  update-pull-request:
  link-sub-issue:
  hide-comment:
---

# pr-review

Once pull request is opened, review the changes against provided description, leave inline comments as necessary, approve or ask for changes otherwise. Once pull request is updated, repeat the same - review the changes, leave comments as necessary and finalise the review by approving it if no more further concerns.

During review it's important to check readability of the code:
- clear variable and method names
- logical and easy to follow structure of the files

It's imiportant to make sure logs are added to the critical decision points
and the right loggin level (INFO, WARN, ERROR) is used, depending on the severity and type of the logged message.

Ensure that there is decent error handling is in place, code should be robust and resilient.

Ensure there are no security concerns - user input is validated and properly escaped, and not used in the unsanitsied SQL expressions.

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
