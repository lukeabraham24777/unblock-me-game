all: paper.pdf

paper.pdf: paper.tex refs.bib generated/*.tex ../figures/*.pdf
	pdflatex -interaction=nonstopmode paper.tex
	bibtex paper
	pdflatex -interaction=nonstopmode paper.tex
	pdflatex -interaction=nonstopmode paper.tex

clean:
	rm -f paper.aux paper.log paper.out paper.bbl paper.blg paper.toc

.PHONY: all clean
