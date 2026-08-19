# Lexipedia legal-process modeling reference — time & advanced objects

Scope: which BPMN/DMN objects carry real legal-process semantics, how to encode them, and
which survive execution in SpiffWorkflow. Two dialects throughout:

- **wiki copy** — full expressive set, optimized for human legibility.
- **execution copy** — restricted to the Spiff-supported subset (§3), lint-enforced (§4).

Support claims are anchored to **SpiffWorkflow 3.0.0**. Pin your version and re-verify §3
before relying on it in the execution copy.

---

## 1. Time (core)

### 1.1 Why time is first-class

Legal procedure is mostly deadlines: response windows, appeal periods, tolling, cooling-off,
limitations, effective dates. In a legal map, a duration without its authority is noise — so
every timer carries a citation, the same merge key used everywhere else in the corpus.

### 1.2 The three placements

| Placement | Legal meaning | BPMN element | Timer form |
|---|---|---|---|
| **Start** | Process instantiates on a date/cycle: statute takes effect, annual filing, periodic review | timer *start* event | `timeDate` / `timeCycle` |
| **Intermediate catch** | Mandatory inline wait: tolling, cooling-off, "no action for N days" | timer *intermediate catch* event | `timeDuration` |
| **Boundary (on a task)** | Deadline attached to an obligation: respond-or-default, cure-or-dismiss | timer *boundary* event | `timeDuration` (usually) |

Boundary timers are **interrupting** (`cancelActivity="true"` — cut the task off, divert) or
**non-interrupting** (`cancelActivity="false"` — fire a reminder/escalation while the task
continues). Timer events are **catch-only**; the clock starts implicitly when the token
reaches the event (or, for boundary, when the attached activity begins).

### 1.3 Timer forms (ISO-8601)

```xml
<!-- duration: wait 30 days (tolling / cooling-off) -->
<bpmn:intermediateCatchEvent id="Toll_30d">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P30D</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>

<!-- date: provision takes effect -->
<bpmn:timeDate xsi:type="bpmn:tFormalExpression">2026-07-01T00:00:00Z</bpmn:timeDate>

<!-- cycle: annual review -->
<bpmn:timeCycle xsi:type="bpmn:tFormalExpression">R/P1Y</bpmn:timeCycle>
```

Durations `PnYnMnDTnHnMnS` (e.g. `P15D`, `PT48H`); dates ISO-8601 instants; cycles `R[n]/…`.

### 1.4 Boundary timer — respond-or-default

Use when there is a **single** obligation with a deadline (no competing inbound event).

```xml
<bpmn:userTask id="AwaitResponse" name="Await party response"/>
<bpmn:boundaryEvent id="Deadline" attachedToRef="AwaitResponse" cancelActivity="true">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P15D</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:boundaryEvent>
<!-- Deadline -> "Enter default"; normal completion -> "Process response" -->
```

### 1.5 The statutory response window — event-based gateway

Use when the deadline **races** an inbound event (a reply may or may not arrive first). This
is the canonical legal-deadline construct: the token waits at an event-based gateway; whichever
fires first — the message or the timer — wins and cancels the other.

```
[Serve notice] --> (X) event-based gateway
                    |-- (message catch) "Response received" --> [Process response]
                    `-- (timer catch)   "P15D elapses"       --> [Enter default / escalate]
```

```xml
<bpmn:eventBasedGateway id="ResponseWindow"/>

<bpmn:intermediateCatchEvent id="ResponseReceived">
  <bpmn:messageEventDefinition messageRef="Msg_Response"/>
</bpmn:intermediateCatchEvent>

<bpmn:intermediateCatchEvent id="DeadlineElapses">
  <bpmn:timerEventDefinition>
    <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P15D</bpmn:timeDuration>
  </bpmn:timerEventDefinition>
</bpmn:intermediateCatchEvent>

<bpmn:sequenceFlow sourceRef="ResponseWindow" targetRef="ResponseReceived"/>
<bpmn:sequenceFlow sourceRef="ResponseWindow" targetRef="DeadlineElapses"/>
```

Boundary timer vs event-based gateway: boundary = deadline *on an activity you're doing*;
event-based gateway = deadline *while waiting for someone else to act*. Most service/notice
windows are the latter.

### 1.6 Contributor → transform promotion

A mail contributor can only hand-draw box/arrow/diamond/circle and **write the deadline in
words** ("respond within 15 days, Rule 33-103.006"). The pipeline promotes that to the timer,
the event-based gateway, and any business-rule typing during transform. The contributor owes
two fields per timed step: the **number** (15 days) and the **authority** (the rule).

---

## 2. Advanced

### 2.1 DMN via business rule task — the primary one

Any **eligibility, qualification, applicability, or classification** decision belongs in a DMN
decision table, not in a fan of exclusive gateways. Gateways route; DMN decides. Keeping the
two separate is what lets the decision logic be edited, versioned, and tested independently of
the process structure.

**Anatomy.** A decision table = input columns (conditions) | output columns (results) | rules
(rows) | **hit policy** (top-left code) governing what happens when multiple rules match.

**Example — exemption applicability (ties to the redaction map).** Decision
`ExemptionApplies`, hit policy **F** (First: rules evaluated top-down, first match wins —
appropriate where more specific rules are ordered above general ones):

| # | `record_type` | `contains_ssn` | → `redact` | `authority` |
|---|---|---|---|---|
| 1 | `"medical"` | `-` | `true` | `"§119.0712(2)"` |
| 2 | `-` | `true` | `true` | `"§119.071(5)(a)"` |
| 3 | `"general"` | `false` | `false` | `"§119.07(1)"` |

`-` means "any". Because rules 1 and 2 can both match (a medical record containing an SSN),
the **hit policy is doing real legal work** — First resolves the overlap deterministically.
Overlap + hit policy is exactly where legal edge cases hide; choose the policy deliberately
(`U` unique, `F` first, `P` priority, `C` collect w/ Sum·Min·Max·Count) and lint for
completeness and unintended overlap.

**BPMN ↔ DMN linkage.** Spiff's business rule task references the decision by id:

```xml
<!-- Spiff extension form -->
<bpmn:businessRuleTask id="DetermineRedaction" name="Determine redaction">
  <bpmn:extensionElements>
    <spiffworkflow:calledDecisionId>ExemptionApplies</spiffworkflow:calledDecisionId>
  </bpmn:extensionElements>
</bpmn:businessRuleTask>

<!-- Camunda form (parsed via the camunda package): camunda:decisionRef="ExemptionApplies" -->
```

Verify the exact extension attribute against your parser (spiff vs camunda business rule task
live in different packages). The table output lands in the task's data and the **next gateway
routes on it** — e.g. `redact == true`.

**FEEL / cell gotchas.**
- Quote string literals (`"medical"`). Unquoted cells are read as **variable names**, not strings.
- Comparisons and ranges are allowed: `> 30`, `[0..90]`, `not("sealed")`.
- Spiff's expression support is a FEEL-flavored subset, not full FEEL — verify operators you rely on.

**DRDs (chained decisions).** When one decision feeds another (eligibility → relief type),
model them as separate decisions. Safest in Spiff: **chain two business rule tasks** (task A's
output is task B's input) rather than leaning on in-DMN information requirements; confirm
multi-decision DRD resolution against your version before relying on it.

**Dialect split.** DMN tables are portable and belong in both copies. Keep the *authority*
column populated so each rule is independently citable — a rule without its statute can't be
merged or audited.

### 2.2 Call activity & subprocess — composition / cross-reference

- **Call activity** invokes another process map by reference. This *is* cross-referencing at
  the execution layer: citation joins fragments, the call activity is the process→process edge.
  Point `calledElement` at the target's id under your `targetNamespace` pattern
  (`https://lexipedia.xyz/{jurisdiction}/{domain}`) so the corpus stays composable instead of
  a pile of standalone maps.
- **Subprocess (collapsed)** encapsulates a phase inline (one map, nested detail).
- **Transaction subprocess** groups steps that must all succeed or compensate — legally, an
  all-or-nothing filing bundle. (Cancel events are only valid inside a transaction.)

```xml
<bpmn:callActivity id="RunAppeal" name="Appeal to Secretary"
    calledElement="Process_FL_Grievance_Appeal"/>
```

### 2.3 Messages & multi-pool — parties and communication

The moment a process has more than one party (petitioner / agency / court), model each as a
**pool** with **message flows** (dashed) between them and **sequence flows** (solid) within.
Service, filing, notice, and receipt are message events. Messages carry a payload and can be
correlated; Spiff even supports intra-process messages, though cross-pool is the standard use.
Multi-pool is how you stop flattening a three-party procedure into one misleading lane.

### 2.4 Error vs escalation boundary — the precise rule

- **Error** = a hard fault: defective/rejected filing, jurisdictional defect. Error events are
  **interrupting only** and **cannot be intermediate**.
- **Escalation** = kick upward without necessarily stopping: bump to a higher authority, notify
  of delay. Escalation events **can be non-interrupting and can be intermediate**.

So: if you need a non-interrupting or intermediate "throw", it has to be escalation, not error.

```xml
<bpmn:boundaryEvent id="DefectiveFiling" attachedToRef="ReviewFiling" cancelActivity="true">
  <bpmn:errorEventDefinition errorRef="Err_Defective"/>
</bpmn:boundaryEvent>

<bpmn:boundaryEvent id="NotifyDelay" attachedToRef="Adjudicate" cancelActivity="false">
  <bpmn:escalationEventDefinition escalationRef="Esc_Delay"/>
</bpmn:boundaryEvent>
```

### 2.5 Event subprocess — scoped interrupts

For an event that can fire *anywhere within a phase* (a jurisdictional deadline that, if it
hits during briefing, collapses the whole phase to dismissal), an **event subprocess** is
cleaner than festooning boundary events across every task in the phase. Verify event
subprocess support in your Spiff version before promoting it to the execution copy.

### 2.6 Terminate end event — hard disposition

A normal end event retires **one** path; a **terminate** end kills **all** live tokens in the
process. Use it deliberately for dismissal, mootness, or final disposition so "the case is
over" reads differently from "this branch finished".

```xml
<bpmn:endEvent id="Dismissed"><bpmn:terminateEventDefinition/></bpmn:endEvent>
```

### 2.7 Multi-instance — cardinality

"For each party / claimant / count / charge." Encodes the cardinality legal maps usually leave
implicit: serve each party, adjudicate each charge.

- **Sequential MI** — one after another (ordered adjudication).
- **Parallel MI** — modeled as concurrent, **but Spiff executes it sequentially** — don't
  design on the assumption of true parallelism.

### 2.8 Data object / data store — documents & docket

- **Data object** — a document flowing through the process (the petition, the record, the
  redacted copy). Data associations show which task produces or consumes it — a ready-made
  provenance substrate for merge analytics.
- **Data store** — the docket / registry / case file. In Spiff the data store is **abstract**:
  parsed, but you implement the read/write. Treat it as an interface, not a built-in.

### 2.9 Text annotation & group

- **Text annotation** — an alternate carrier for the authority citation if you ever want it off
  the element label; also for scope notes ("tolled during appeal").
- **Group** — a visual box with no execution semantics; use it to mark statutory phases
  ("pre-filing", "administrative exhaustion") without changing flow.

### 2.10 Gateways beyond XOR

- **Parallel (AND)** — concurrent obligations that must all complete (serve all parties, file
  in all courts) before proceeding.
- **Inclusive (OR)** — one-or-more paths taken by condition. Historically Spiff supported
  converging inclusive only; verify diverging splits in your version.
- **Event-based** — the response-window race (§1.5).
- **Complex** — avoid; not supported and rarely needed.

---

## 3. SpiffWorkflow support matrix (3.0.0 — verify against your pin)

| Element | Supported | Note |
|---|---|---|
| User / Manual / Script task | ✓ | executed |
| Business Rule task (DMN) | ✓ | decision table executed directly |
| Service task | ⚠ | parsed but abstract — you supply execution |
| Exclusive / Parallel gateway | ✓ | |
| Inclusive gateway | ✓ | historically converging-only; verify diverging split |
| Event-based gateway | ✓ | |
| Complex gateway | ✗ | not supported |
| Subprocess / Call activity / Transaction subprocess | ✓ | |
| Event subprocess | ⚠ | verify in your version |
| Ad-hoc subprocess | ✗ | not supported |
| Timer event (start / intermediate / boundary) | ✓ | catch-only; interrupting & non-interrupting boundary |
| Message event | ✓ | carries payload; intra- and cross-process |
| Signal event | ✓ | broadcast; good for a ruling affecting parallel matters |
| Error event | ✓ | interrupting only; no intermediate |
| Escalation event | ✓ | may be non-interrupting / intermediate |
| Terminate event | ✓ | kills all tokens |
| Cancel event | ✓ | transaction subprocess only |
| Conditional event | ✗/⚠ | not in the 3.0.0 list — verify |
| Compensation event | ✗ | not supported |
| Data object | ✓ | |
| Data store | ⚠ | parsed but abstract — you supply read/write |
| Loop task | ✓ | |
| Sequential multi-instance | ✓ | |
| Parallel multi-instance | ⚠ | parsed but **executed sequentially**, not in parallel |

Legend: ✓ executes · ⚠ parses with a caveat / you implement · ✗ unsupported.

---

## 4. Lint hooks for `bpmnlint-plugin-lexipedia`

Extends the existing four rules (legal-reference-required, wikidata-reference,
wikidata-id-format, statutory-gap):

- **timer-iso8601** — every `timerEventDefinition` has a valid ISO-8601
  `timeDuration` / `timeDate` / `timeCycle`. (error)
- **deadline-has-authority** — any timer modeling a legal deadline carries a citation. (error)
- **business-rule-has-decision** — every `businessRuleTask` resolves to a known decision
  (`calledDecisionId` / `decisionRef`). (error)
- **decision-authority-per-rule** — every DMN rule row has a populated authority output. (warn)
- **decision-table-well-formed** — completeness + overlap check against the declared hit
  policy (overlap under `U`, or gaps, are flags). (warn)
- **call-activity-resolvable** — `calledElement` resolves to a process in the corpus under the
  `targetNamespace` pattern. (error)
- **execution-tier-spiff-safe** — no element outside the §3 supported set appears in the
  execution copy (complex gateway, compensation, ad-hoc, conditional → error); keeps the two
  dialects from silently drifting. (error, execution copy only)
- **flow-kind-by-scope** — `messageFlow` only crosses pools; `sequenceFlow` only stays within
  one. (error)

---

## 5. Sources / verify

Element and DMN support drawn from the SpiffWorkflow 3.0.0 "List of Supported Elements",
Spiff decision-table and events reference docs. SpiffWorkflow moves; treat §3 as a snapshot,
pin your version, and confirm the ⚠/✗ rows before they reach the execution copy. Dan Funk
(Sartography) is the authoritative check for anything ambiguous here.
