---
name: dev-us
description: "Builds one validated user story of a Cockpit project from its acceptance criteria to an open pull request: tests first, implementation, review, then the pull request, reporting every step to Cockpit. Use it as /dev-us <project> <issue-number>, or when asked to develop a user story or a ticket kept in Cockpit."
---

# Develop a user story kept in Cockpit

Arguments: `$ARGUMENTS`: the project (its Cockpit slug) and the number of the GitHub issue of the user story, possibly followed by extra instructions from the owner of the repository.

You build one user story, from its acceptance criteria to an open pull request, and you report every step to Cockpit through the tools of the `cockpit` MCP server, where the owner follows your work. You never merge.

If the `cockpit` tools are not available in this session, stop and say so: nothing can be done without them.

## 1. Preflight (local session only)

A cloud session (the environment variable `CLAUDE_CODE_REMOTE` is `true`) works on a fresh clone: skip this step there.

In a local session, check the clone before touching anything, and keep the three results for step 3:

1. **Right repository.** Call `get_project` with the project: it gives its repo. `git remote get-url origin` must point to that repo. If it does not, stop: say which repository this directory is and give the `git clone` command of the right one.
2. **Clean working tree.** `git status --porcelain` must print nothing. If it does, stop and list the files: never stash, commit or discard changes you did not make.
3. **Up to date.** `git fetch origin`, then bring the default branch to its remote by fast-forward only (`git checkout <default> && git merge --ff-only origin/<default>`). If it cannot be fast-forwarded, stop and say why.

## 2. Read the user story

Call `get_user_story` with the project and the issue number. It returns the story, its acceptance criteria (each with an `id`) and its status.

If the status is not `ready`, stop here: say what its status is and that only a story its owner validated can be developed. Do not call `start_run`.

## 3. Start the run

Call `start_run` with the id of the story, the model you run on, `preflight` (the three results of step 1, in a local session) and `target: "cloud"` in a cloud session. In a cloud session also give `sessionId`, the value of the environment variable `CLAUDE_CODE_REMOTE_SESSION_ID`: Cockpit recognises the cost of the session by it. If the call is refused, stop and report the reason: another run may already be at work on this story.

If the answer carries a `warning`, the story depends on stories that are not done yet. Go on when the work can be done without them; otherwise ask the owner with `ask_user` before writing any code.

The answer gives the run: its `id`, the branch to work on (`branchName`), its base (`baseBranch`) and `extraPrompt`, what the owner asks for this run in particular. Follow `extraPrompt`.

Check out the branch: `git fetch origin`, then `git checkout <branchName>` when origin has it, otherwise `git checkout -b <branchName> origin/<baseBranch>`. All the work happens on this branch.

## 4. Tests first: test-writer

Give the story, its criteria and the conventions of the project (`CLAUDE.md`, `.claude/rules/`) to the **test-writer** subagent. It writes the acceptance tests, at least one per criterion, **before any implementation**. Run them: every new test must fail, and fail because the feature is missing. Commit the tests.

## 5. Implementation: developer

Give the story, the criteria and the failing tests to the **developer** subagent. It implements until the acceptance tests pass, adds unit tests where logic is not covered, and never weakens an acceptance test. Commit.

## 6. Review: reviewer

Give the story, the criteria and the base branch to the **reviewer** subagent, in a fresh context: it did not write the code. It reviews the diff of the branch against its base, the criteria and `CLAUDE.md`.

If it reports findings that must be fixed, give them to the developer subagent, then have the reviewer look again. After three rounds without a clean review, do not loop: ask the owner with `ask_user`, or close the run as `needs_check` with the open findings in the summary.

## 7. Check and report the criteria

Run the full test, lint and type-check commands of the project (see `CLAUDE.md`). Then call `report_criterion` for **every** criterion of the story, with its `id`, `passed` or `failed`, and its evidence: the file and the name of the test that proves it.

## 8. Pull request

1. Push the branch: `git push -u origin <branchName>`.
2. Open the pull request against `baseBranch`. Title: the title of the story. Body: a line `Closes #<issue-number>`, the link to the user story in Cockpit (its `url`), a summary of what was built and of the tests that were run. In a local session, `gh pr create`. In a cloud session `gh pr` is rejected: use the GitHub tools of the session, or `gh api repos/<owner>/<repo>/pulls` with `title`, `head`, `base` and `body`. If the branch already has an open pull request (the run is a relaunch), push to it and keep its number.
3. Call `link_pull_request` with the number of the pull request.
4. Call `finish_run`: `succeeded` when every criterion passed; `needs_check` when the work is done but something needs the owner's eye (a criterion you could not prove, a choice you made for them). The summary says what was built, which tests were run with their result, and what is left or uncertain.

## 9. Stop

The run is over when the pull request is open. Never merge it: merging is the owner's decision.

## Throughout the run

- **Report every step.** Call `report_step` when a step starts (`running`) and when it ends (`succeeded` or `failed`, with a short summary): steps 4 to 8, with the agent that does it (`test-writer`, `developer`, `reviewer`, or `main` for yourself) and a title in the language of the story. Keep the same agent and title to update a step.
- **Obey a stop request.** Read the answer of each `report_step`: when it carries `stopRequested`, stop at once. Do not start another step, do not push, do not open a pull request. Call `finish_run` with `stopped` and say where things stand: what is committed, what is not. The owner asked for the stop, or the run reached its budget cap: the answer says which, and so does your summary.
- **Ask rather than guess.** When a decision belongs to the owner (an ambiguity in the story, a choice the criteria do not settle), call `ask_user` with one clear question and the options you see, then `get_answer` about once a minute until it is answered. Meanwhile, go on with what does not depend on the answer.
- **Never leave a run open.** If you cannot finish, call `finish_run` with `failed` and say why.
- **Subagents.** If no subagent has the expected name in this session, read its definition in the repository (`.claude/agents/<name>.md`, or `agents/<name>.md`) and give it to a general-purpose subagent as its instructions.
- Never merge a pull request, never push to the default branch, never force-push and never delete a branch.
