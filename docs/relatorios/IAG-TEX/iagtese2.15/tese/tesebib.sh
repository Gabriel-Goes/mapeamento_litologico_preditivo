latex tese.tex 
bibtex tese.aux
latex tese.tex 
latex tese.tex 
echo "Ola $USER, estou gerando o arquivo .pdf"
dvipdf tese.dvi 
rm tese.bbl tese.blg tese.lof tese.lot tese.toc tese.aux tese.dvi  tese.log tese.out
echo "Pronto!"



