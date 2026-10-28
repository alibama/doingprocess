# Process models

The BPMN maps and DMN tables behind the "Starting a business after release" pages on
doingprocess.org. Virginia is the first worked example. **Every file here is a draft**:
citations marked `?` in the specs render as *citation needed*, and nothing has been
signed off by a reviewer yet.

| Path | What |
|------|------|
| `src/*.json` | The source of each map: nodes on a grid, flows, lanes, citations. Edit these. |
| `*.bpmn` | Generated BPMN 2.0 with diagram interchange. Opens in bpmn.io, Camunda Modeler, SpiffWorkflow. |
| `dmn/*.dmn` | Hand-written DMN 1.3 decision tables (hit policy FIRST). |
| `../site/assets/diagrams/*.svg` | Generated pictures used by the site. |
| `../site/models/` | Copies of the `.bpmn` and `.dmn` files served for download. |

## Rebuild

```bash
python tools/build_diagrams.py      # from the repo root; standard library only
```

`./update.sh` runs this for you before committing.

## Spec format

One JSON object per map. The header comment of `tools/build_diagrams.py` documents every
field. The short version:

- `nodes[]` have an `id`, a `type`, a `name`, and a grid position `col`/`row`
  (fractions allowed). Types: `start`, `timer-start`, `end`, `timer`, `message`,
  `xor`, `and`, `event`, `task`, `user`, `service`, `script`, `rule`, `manual`,
  `subprocess`, `boundary-timer` (needs `attached`), `note` (needs `text`, optional `for`).
- `cite` is the authority behind a step (`"Va. Code § 46.2-345"`, `"Survey C1"`).
  Use `"?"` when it is still missing: the site shows *citation needed* and the BPMN
  documentation says `CITATION NEEDED`, so the lint rule can find it.
- `inside: true` marks a step that can start before release (green tag).
- `who` adds a small role label above a step in lane-less maps.
- `lanes[]` give each lane a `name` and the `rows` it covers.
- `flows[]` connect `from` → `to`, with an optional `name` (branch label), `via` grid
  points the line must pass through, and `join: true` to stop the arrow on the last
  via point (merging into another line instead of entering the shape).

## Adding a state

1. Copy `dmn/licensing_barrier.dmn` and replace the authorities with the state's
   licensing statute (most states now have a direct-relationship test; a few still allow
   blanket bans).
2. Add `license_required.dmn` (trade → licence, permit, inspection) and
   `entity_choice.dmn` (ownership answer → filing) for the state.
3. Fork `src/obtain_id.json`: the DMV, vital-records and reinstatement steps differ most.
   Many states still suspend licences for unpaid court debt; Virginia does not.
4. Mark every citation you are not sure of with `?`, then find a reviewer.
