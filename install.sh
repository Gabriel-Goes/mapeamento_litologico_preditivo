#!/bin/bash

# Definindo o caminho do projeto
PROJETO="$HOME/projetos/PreditorTerra"

# Clonando o repositório
echo "Clonando o repositório..."
if ! command -v git &> /dev/null
then
    echo "Git não encontrado. Tentando instalar..."

    # Verifica se o sistema usa pacman
    if command -v pacman &> /dev/null
    then
        sudo pacman -S git
    echo "Git instalado com sucesso!"
    else
        echo "Não foi possível instalar o Git automaticamente."
        echo "Por favor, instale o Git manualmente visitando: https://git-scm.com/downloads"
        exit 1
fi
#
# Verifica se o Python está instalado
# Se não estiver, tenta instalar
if ! command -v python3 &> /dev/null
then
    echo "Python não encontrado. Tentando instalar..."

    # Verifica se o sistema usa pacman
    if command -v pacman &> /dev/null
    then
        sudo pacman -S python
    echo "Python instalado com sucesso!"
    else
        echo "Não foi possível instalar o Python automaticamente."
        echo "Por favor, instale o Python manualmente visitando: https://www.python.org/downloads/"
        exit 1
fi

# Verifica se o pip está instalado
# Se não estiver, tenta instalar
if ! command -v pip &> /dev/null
then
    echo "Pip não encontrado. Tentando instalar..."

    # Verifica se o sistema usa pacman
    if command -v pacman &> /dev/null
    then
        sudo pacman -S python-pip
    echo "Pip instalado com sucesso!"
    else
        echo "Não foi possível instalar o Pip automaticamente."
        echo "Por favor, instale o Pip manualmente visitando: https://pip.pypa.io/en/stable/installation/"
        exit 1
    fi
fi

# Criação de um ambiente virtual
echo "Criando ambiente virtual..."
python3 -m venv "$HOME/.config/geo"

# Ativação do ambiente virtual
$ALIAS_COMMAND="alias geo=source '$HOME/.config/geo/bin/activate'"
grep -qxF "$ALIAS_COMMAND" ~/.bashrc || echo "$ALIAS_COMMAND" >> ~/.bashrc
echo "Alias 'geo' adiconado ao .bashrc"
echo "Ativando ambiente virtual..."
source "$HOME/.config/geo/bin/activate"

# Instalação das dependências
echo "Instalando dependências do Python..."
python3 -m pip install -r "$PROJETO/dotfiles/requirements.txt"

echo "Instalação concluída com sucesso!"
