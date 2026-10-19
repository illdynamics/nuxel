# Owner acceptance

**PENDING. No owner PASS has been received.**

After an announced trial, run from the repository:

```
tools/touchable/touchable-owner PASS
tools/touchable/touchable-owner FAIL "Describe the visible failure"
```

The command appends a timestamped record scoped to the current trial in
`owner-feedback.jsonl`. `--trial <id>` can identify an earlier trial explicitly.
The runner reads it after capture and stores it in that trial's result.json.
Late feedback remains in the append-only ledger and must also be reviewed.
Chat feedback may be recorded only by quoting an actual owner response.

Trial `tap-before-20261018t2307`: feedback requested; no response yet.
