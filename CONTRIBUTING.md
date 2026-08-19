# Contributing to Doing Process

Thanks for helping. There are two kinds of contribution, with different paths.

## 1. Code & tooling (pull requests)

The processing pipeline lives in `intake/`. Good first contributions:

- **A recognizer backend** — implement `RecognizerBackend` in
  `intake/recognizer.py` (`available()` + `draft_bpmn(image_path) -> bpmn_xml`),
  register it in `get_backend()`, and add a test. Keep it **local** — a backend
  that phones a cloud service won't be accepted for the contributor-facing path.
- **A lint rule** — add a rule in `intake/lint.py` following the existing ones
  (structural, namespace-agnostic, with a clear message) and a test case.
- **Pipeline / layout / provenance** improvements — with tests.

### Ground rules

- **Local-first.** No component may send a scan, draft, or contributor detail to
  a third-party service. OCR and recognition run on owned hardware or not at all.
- **Deterministic & regenerable.** Prefer stdlib; pin behavior with tests.
- **Human sign-off stays.** Recognition may be automated; publication is not.
- **Tests pass.** Run `cd intake && ./scripts/smoke_test.sh` before opening a PR.
  CI runs the deterministic suite on every push.
- **License.** By contributing code you agree it's licensed under Apache-2.0.

### Dev setup

```bash
cd intake
./scripts/setup.sh        # deps (+ optional model pull)
./scripts/smoke_test.sh   # core, parse, pipeline, layout, service — all offline
```

Open a PR with a clear description and, where it helps, a before/after or a test
that captures the behavior.

## 2. Process maps (the mail flow)

Most map contributors are working on paper, often by mail, not on GitHub. That
path is run by **operators**, not through this repo directly:

1. A contributor draws a map following the [handbook](handbook/) /
   [contributor packet](site/doingprocess-contributor-packet.pdf).
2. An operator scans it and runs it through `intake/` (recognize → lint →
   redact → sign off).
3. The signed, CC0 map enters the corpus.

If you want to **operate an intake** (a clinic, a reentry program, a facility
partner), open an issue or email — we'll help you stand up the local pipeline.

## Reporting problems

Bugs and ideas: open an issue using the templates. Security or privacy concerns:
see [SECURITY.md](SECURITY.md) — please don't file those publicly.

## Code of conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). This
project works with a vulnerable contributor population; we hold a high bar for
respect, privacy, and care.
