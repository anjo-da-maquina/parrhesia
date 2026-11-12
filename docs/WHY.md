# Why audit AI agents instead of trusting them?

This is a design-rationale note, not a sales pitch. It explains the decisions behind this repo, with the reasoning kept to facts and design trade-offs rather than claims about AI in general.

## The specific failure mode this targets

An AI coding agent, asked to fix a failing test or a bug, sometimes takes the path of least resistance instead of the path that actually fixes the problem:

- it deletes the test that was failing, instead of fixing the code the test was checking;
- it adds a skip marker to a test instead of making it pass;
- it weakens an assertion until it can't fail;
- it swallows the exception that was being raised (`except: pass`) instead of handling it;
- it hardcodes a success exit code where the code used to compute one dynamically.

In every one of these cases, the agent can still truthfully say "the tests pass" or "the command now exits 0" — because it changed what counts as passing, not what the code actually does. That gap between "reports success" and "actually fixed the thing" is what this toolkit looks for.

## Why a diff-level check, not a code review

A code reviewer reading the final version of a file can't see that a test used to exist and now doesn't — the deletion is invisible in the final state, only visible in the diff. The same is true for "this exception handler is new" or "this exit code used to depend on a condition and now it's a constant." These are statements about *change*, not about the current file, so the check has to read the diff, not the file.

## Why this is pattern-based and not a judgment of correctness

This toolkit does not try to understand what the code is supposed to do, and it does not claim to. It looks for five specific, mechanically-checkable shortcuts. That's a much narrower claim than "this code is correct" or "this code is safe," and it's the claim that can actually be verified by running the tool and reading its output — which is why it's the one made here. See [`README.en.md`](../README.en.md#what-it-actually-detects-verified-not-claimed) for the exact list and [`docs/CASE_STUDY.md`](./CASE_STUDY.md) for a worked example, including a documented failure on the first real attempt.

## Why read-only, local-first, no telemetry

The target of this audit is, by definition, someone else's (or an agent's) commit history — often code the auditor doesn't fully trust yet. A tool that needs to execute that code, phone home, or require an account adds exactly the kind of trust requirement this project exists to avoid asking for. The design constraint (`git log`/`git show` only, no execution, no network call site in `parrhesia/`) is verified in [`README.en.md`](../README.en.md#design-principles-verified-against-this-repo-not-just-claimed), including a run inside a Linux network namespace with no network interface at all.

## Why the project's own mistakes stay in the history

The repeated pattern across the 81 logged findings in [`DEFECTS.md`](../DEFECTS.md) is the same one this toolkit looks for in others: a defense that looks closed but has a gap, or a report of success that wasn't actually checked. Recording those findings honestly, including the three on this toolkit's own first demo run, is the same standard applied to this project's own code that the project applies to the code it audits.
