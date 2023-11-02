latex tese.tex 
latex tese.tex 
latex tese.tex 
echo "Ola $USER, estou gerando o arquivo .pdf"
dvipdf tese.dvi 
rm tese.lof tese.lot tese.toc tese.aux tese.dvi  tese.log
echo "Pronto!"

