##################################################
#!/bin/bash					 #
#						 #
# Script para instalar os arquivos do IAGTESE    #
#						 #
# Autor: Vinicius Placco (vmplacco)		 #
#  						 #
# data: 09/10/2008  				 #
#						 #
##################################################

pathcls=`find /usr/ -name article.cls | grep base | sed -e 's=article.cls==g'`
pathbib=`find /usr/ -name plain.bst | grep base | sed -e 's=plain.bst==g'`
pathcap=`find /usr/ -name caption.sty | grep usr | sed -e 's=caption.sty==g'`

cp -p iagtese.cls iagtese_en.cls bibliografia.sty bibliografia_en.sty fancyhdr.sty fncychap.sty deluxetable.sty longtable.dtx $pathcls
cp -p iag.bst iag_en.bst $pathbib
cp -p caption.sty caption3.sty $pathcap
texhash

echo "Pronto!"
