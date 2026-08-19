# Doing Process — convenience targets
.PHONY: help setup test app cli elca annotator site handbook

help:
	@echo "make setup      install intake deps (+ optional model pull)"
	@echo "make test       run the deterministic test suite (offline)"
	@echo "make app        launch the review station UI"
	@echo "make elca       run the local detector service"
	@echo "make annotator  run the local box-correction UI"
	@echo "make handbook   rebuild the handbook PDF"
	@echo "make site       serve site/ locally on :8000"

setup:
	cd intake && ./scripts/setup.sh
test:
	cd intake && python tests/test_core.py && python tests/test_vlm_parse.py && \
	  python tests/test_pipeline_mock.py && python tests/test_layout.py && \
	  python tests/test_serve_fake.py
app:
	cd intake && ./scripts/run_app.sh
cli:
	cd intake && ./scripts/run_cli.sh
elca:
	cd intake && ./scripts/run_elca.sh
annotator:
	cd intake && ./scripts/run_annotator.sh
handbook:
	cd handbook && python build_handbook.py
site:
	cd site && python3 -m http.server 8000
