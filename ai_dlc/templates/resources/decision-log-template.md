# Decision Log: <unit-of-work id>

Append-only. One entry per gate passed (Inception → Construction, Construction → Review,
Review → Operations). This is the audit trail — don't edit past entries, add new ones.

## Entry format

```
### <date> — <gate name>

- Spec version: requirements.md v<n>, design.md v<n>
- Approver: <name> (must not be the person/session that authored the artifact being approved)
- Eval result: <pass/fail against requirements.md Acceptance Criteria — link to test run or
  paste output>
- Verdict: approved / rejected / approved with changes
- Notes: <anything a future reader needs — why a rejection happened, what changed on
  resubmission>
```

## Log

<Add entries below, newest last.>
