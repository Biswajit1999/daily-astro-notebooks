# LaTeX source for the Euclid reports

The manuscripts use A&A `aa.cls` version 9.4 (2025-11-27), the `aa.bst` author–year BibTeX style, `graphicx`, `txfonts`, and `hyperref`. Obtain the publisher’s template files from [Astronomy & Astrophysics](https://www.aanda.org/for-authors/latex-issues/information-files) or use the supplied template archive. Place `aa.cls`, `linenoaa.sty`, and `aa.bst` on your TeX search path. The manuscript figures are resolved relative to this directory.

Run these commands here, substituting `day2` or `day3` to build the other reports.

```bash
pdflatex -interaction=nonstopmode -halt-on-error day1.tex
bibtex day1
pdflatex -interaction=nonstopmode -halt-on-error day1.tex
pdflatex -interaction=nonstopmode -halt-on-error day1.tex
```
