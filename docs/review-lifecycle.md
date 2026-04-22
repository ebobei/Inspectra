# Review lifecycle

Inspectra maintains one review session per tracked source object.

## Initial review
- fetch source
- normalize content
- create source snapshot
- run LLM review
- persist findings
- publish one external comment

## Recheck
- fetch the updated source
- compare hash against the last successful input
- skip if nothing changed
- re-run review if changed
- merge findings:
  - resolved findings are closed
  - unresolved findings stay open
  - new findings are added
- update the same external comment

## Iteration limit
Each session has `max_iterations`.

When the limit is reached, Inspectra stops doing full re-review and publishes a short summary-only update instead.

That prevents endless passive-aggressive review loops.

## Terminology
- **Session**: one tracked review lifecycle for one external source object
- **Review run**: one execution attempt against one snapshot
- **Finding**: one managed review concern that can stay open or become resolved
- **Publication**: one create/update/noop attempt for the external comment
