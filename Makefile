report: report.tex
	mkdir -p output_report
	pdflatex -interaction nonstopmode --output-dir output_report report.tex
	pdflatex -interaction nonstopmode --output-dir output_report report.tex
	mv output_report/report.pdf .

clean:
	rm -rf output_report report.pdf
