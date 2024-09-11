#!/bin/bash


# Predito Terra ( Mapeamento Litológico Preditivo )
# Reads data, outputs classes.
#

pushd $HOME/projetos/PreditorTerra/

if [ ! -d $HOME/.local/bin/app ]; then
    cp app $HOME/.local/bin/
fi

python fonte/nucleo/interface.py
