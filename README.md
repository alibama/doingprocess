# Doing Process

**Doing process is due process.** Doing Process turns hand-drawn maps of legal
processes — many of them drawn by people inside prisons — into a public,
machine-readable encyclopedia of how the law actually works.

A legal process is a sequence: who does what, in what order, under which law.
People who navigate the system up close understand these processes intimately,
and that knowledge is usually invisible and uncredited. This project captures it
as **BPMN** process maps that can be scanned, recognized into a machine-readable
model, checked against the law each step cites, and published under CC0.

**First worked example: starting a business after release.** The site maps the
whole road — ID, bank account, ownership form, licences, taxes, money, benefits —
as BPMN with the law behind each step, and pairs it with a readiness survey whose
answers pre-fill a person's path. Virginia is the first state. Every map is a
draft until a reviewer signs off; missing authorities say *citation needed*.

Everything here runs **locally** — recognition, OCR, checking, and storage on
your own hardware, so material from contributors never depends on a third party.

## What's in the repo

| Path | What it is |
|------|------------|
| `site/` | The `doingprocess.org` website: three static pages, shared CSS, generated diagrams, downloadable models and PDFs. |
| `models/` | The BPMN/DMN models: JSON specs in `models/src/`, generated `.bpmn`, hand-written `.dmn`. See [`models/README.md`](models/README.md). |
| `tools/build_diagrams.py` | Turns the specs into SVG for the site and BPMN 2.0 XML. Standard library only. |
| `update.sh` | One command to rebuild, commit and push. GitHub Pages redeploys. |
| `intake/` | The local processing pipeline: scan → recognize → lint → provenance → sign-off. A Streamlit app **and** a headless CLI. |
| `handbook/` | The handbook (`build_handbook.py` regenerates the PDF). |
| `packets/` | Print-and-mail contributor packet generators. |
| `docs/` | Reference material, incl. the BPMN/DMN modeling guide. |

## Update the website

Apache on the server points at `/var/www/doingprocess/site`, so deploying is a pull:

```bash
cd /var/www/doingprocess && bash update.sh      # on the server: pull the latest
```

From your own machine, after editing the HTML in `site/`, the maps in `models/src/*.json`
or the stylesheet in `site/assets/site.css`:

```bash
bash update.sh --push "What changed"           # rebuild diagrams, commit, push
bash update.sh --preview                       # look at it first on http://localhost:8000
```

The script finds a Python 3 on its own (including the Windows install) and skips the
diagram rebuild if none is available. Anything the site later needs at deploy time belongs
in the `pull` step of `update.sh`, so the server command stays the same. GitHub Pages is an
optional mirror: `.github/workflows/pages.yml` runs only when started by hand from the
Actions tab, and needs *Settings → Pages → Source = GitHub Actions* first.

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
  document that flow. To fix or extend the business start-up maps directly, edit
  `models/src/*.json` and open a pull request.

## Licensing

- **Code:** Apache-2.0 — see [LICENSE](LICENSE).
- **Contributed process maps & content:** CC0-1.0 (public domain) — see
  [LICENSE-CONTENT](LICENSE-CONTENT).

## Privacy

This repo contains **no contributor data**. Scanned originals and any legal
identity stay in a restricted archive outside version control (`.gitignore`d).
Recognition is automatic; a human signs off before anything is published.

Built on open standards and projects: BPMN & DMN, SpiffWorkflow, bpmn-js, hdBPMN,
and the ELCA sketch-to-BPMN detector. Part of the Lexipedia project.
