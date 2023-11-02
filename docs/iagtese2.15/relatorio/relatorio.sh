latex relatorio.tex 
bibtex relatorio.aux
latex relatorio.tex 
latex relatorio.tex 
echo "Ola $USER, estou gerando o arquivo .pdf"
dvipdf relatorio.dvi 
rm relatorio.aux relatorio.blg relatorio.log relatorio.bbl relatorio.dvi
echo "Pronto!"
