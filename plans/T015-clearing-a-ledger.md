# T015 - Clearing a ledger is all or nothing

**Clearing a ledger is all or nothing.**
`DiagnosisRunner.async_clear_ledger` clears the capability ledger **and**
removes the plausibility store with it, so an owner who wants the runs
afresh loses every reading the checks have gathered too -- at the
maintainer's on 2026-11-17 that would have been a day of polls and three
settled V x I checks. Worth separating, or offering per check.

**Not urgent, and no longer the remedy for a wrong verdict.** That is
what `CHECK_REVISIONS` is for (`capability_test/coverage.py`): each check
carries a revision, a run records the revisions it was measured with, and
`ledger.py` keeps only rows measured at the current one, so raising a
number makes every ledger ask that check again -- and only that one -- on
update, with no clearing and nothing for a user to do. The step-as-clamp
fix of 2026-11-17 raised the seven bound checks to 2 accordingly, and
`tests/test_capability_ledger.py::test_a_bound_clamped_under_the_old_rule_is_asked_again`
holds the rule and the bump together.

The lesson, since it was nearly missed: **a change that could change a
verdict needs its revision raised in the same commit**, which the table's
own docstring says and the first fix did not do.

**Readings checks have their own revisions now** (`CHECK_REVISIONS` in
`capability_test/plausibility.py`, not the one in `coverage.py`), raised
for `daily counters reset at midnight` by the clock fix. That takes the
urgency out of this item from the other side: a *wrong* readings verdict
no longer needs the store cleared, so what is left here is only the
owner's own wish to start the runs afresh without losing days of
readings.
