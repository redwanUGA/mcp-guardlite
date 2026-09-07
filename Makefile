.PHONY: install test data sentinel eval tables paper
install:  ; pip install -e .
test:     ; pytest -q tests/
data:     ; sbatch scripts/gen_data.slurm
sentinel: ; python -m mcpguardlite.cli train-sentinel --data data/ --out models/sentinel/
eval:     ; python -m mcpguardlite.cli eval --spec configs/runs/rq1.yaml --out results/
tables:   ; python -m mcpguardlite.cli tables --results results/ --out paper/tables.tex
paper:    ; cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
