# Doing Process

**Doing process is due process.** Doing Process turns hand-drawn maps of legal
processes — many of them drawn by people inside prisons — into a public,
machine-readable encyclopedia of how the law actually works.

A legal process is a sequence: who does what, in what order, under which law.
People who navigate the system up close understand these processes intimately,
and that knowledge is usually invisible and uncredited. This project captures it
as **BPMN** process maps that can be scanned, recognized into a machine-readable
model, checked against the law each step cites, and published under CC0.

Everything here runs **locally** — recognition, OCR, checking, and storage on
your own hardware, so material from contributors never depends on a third party.

## What's in the repo

| Path | What it is |
|------|------------|
| `intake/` | The local processing pipeline: scan → recognize → lint → provenance → sign-off. A Streamlit app **and** a headless CLI. |
| `site/` | The `doingprocess.org` website (self-contained `index.html` + the downloadable PDFs). |
| `handbook/` | The handbook (`build_handbook.py` regenerates the PDF). |
| `packets/` | Print-and-mail contributor packet generators. |
| `docs/` | Reference material, incl. the BPMN/DMN modeling guide. |

## Do local processing (quickstart)

```bash
git clone <your-fork-url> doingprocess
cd doingprocess/intake

./scripts/setup.sh        # python deps + pull the local vision model (qwen3.6 on Ollama)
./scripts/smoke_test.sh   # verify everything offline (no model needed)
./scripts/run_app.sh      # the review station UI  (needs Ollama for auto-draft)
```

Batch a folder of scans headlessly:

```bash
python cli.py scans/ --backend local-vlm --outdir corpus_staging   # local vision model
python cli.py scans/ --backend mock --sign "you" --outdir out       # offline, deterministic
```

**Detector track (renders as drawn, highest fidelity).** Run the purpose-built
detector as a local service — clones the open ELCA model, bypasses its cloud OCR:

```bash
./scripts/run_elca.sh
python cli.py scans/ --backend elca --endpoint http://127.0.0.1:8600/recognize
```

See [`intake/README.md`](intake/README.md) for the full pipeline, the two
recognizer tracks, and the local-first / no-cloud details.

## The path a map travels

1. **Draw** — one process per page; a step, its role, and the rule it cites.
2. **Mail & scan** — mailed in, scanned, deskewed, cleaned.
3. **Recognize** — a local model turns the drawing into BPMN. Never a cloud.
4. **Check** — a linter enforces real deadlines and a citation on every step.
5. **Sign off** — a person corrects, redacts, and releases under CC0.
6. **Publish** — the map enters the corpus, merged and cross-referenced.

## Two ways to contribute

- **Code & tooling** — via pull request. See [CONTRIBUTING.md](CONTRIBUTING.md):
  add a recognizer backend, a lint rule, or improve the pipeline.
- **Process maps** — most map contributors are working on paper by mail, not
  GitHub. Operators digitize those maps through `intake/`. The
  [handbook](handbook/) and the [contributor packet](site/doingprocess-contributor-packet.pdf)
  document that flow.

## Licensing

- **Code:** Apache-2.0 — see [LICENSE](LICENSE).
- **Contributed process maps & content:** CC0-1.0 (public domain) — see
  [LICENSE-CONTENT](LICENSE-CONTENT).

## Privacy

This repo contains **no contributor data**. Scanned originals and any legal
identity stay in a restricted archive outside version control (`.gitignore`d).
Recognition is automatic; a human signs off before anything is published.

## Publishing the site

`site/` is static. Point GitHub Pages (or any host) at it; the PDF download
links are relative, so keep the three files together.

Built on open standards and projects: BPMN & DMN, SpiffWorkflow, bpmn-js, hdBPMN,
and the ELCA sketch-to-BPMN detector. Part of the Lexipedia project.
