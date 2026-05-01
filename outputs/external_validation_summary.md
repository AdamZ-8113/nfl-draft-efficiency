# External Validation Summary

- Validation source: `ESPN roster` and `ESPN depth chart`
- Players checked: `1294`
- Teams fetched successfully: `32`
- Teams with fetch errors: `0`
- Roster membership mismatches: `119`
- Current depth-chart starter advisories: `54`

## Notes

- `roster_membership_mismatch` means the pipeline and ESPN disagree on whether the player is currently with his drafting team.
- `current_depth_chart_starter_not_historical_starter` is advisory: ESPN marks the player as a current first-team depth-chart starter, but the pipeline's historical snap-count starter flag is still false.

## Fetch Errors

- None
