# Preditor Terra

## Sobre o Projeto

Projeto que visa a produção de um sistema dinâmico de produção de mapas
preditivos, no qual, ao se disponibilizar novos dados, novas predições serão
geradas.

![image](/home/ggrl/projetos/PreditorTerra/docs/uml/uml_projeto.png)


## Estrutura do Repositório
O Repositório está estruturado em 4 caminhos principais:

```
   docs
  dotfiles
  dotfiles
  jupyternotebooks
  source
   README.md   # Você está aqui!
```
- [docs](https://github.com/Gabriel-Goes/mapeamento_litologico_preditivo/tree/main/docs) -- Documentos que fornecem informações sobre o projeto, assim
como relatórios de pesquisa, resumos e pôsters de eventos.
- [dotfiles](https://github.com/Gabriel-Goes/mapeamento_litologico_preditivo/tree/main/dotfiles) --  Arquivos de configuração do ambiente de programação, como
o environment.yml que serve para configurar o ambiente virutal do python com
conda, e o arquivo requirements.txt para configurar o ambieten virtual com
pyenv diretamente. (~~Recomendável~~)
- [jupyternotebooks](https://github.com/Gabriel-Goes/mapeamento_litologico_preditivo/tree/main/jupyternotebooks) -- Scripts de tutoriais e teste de código.
- [source](https://github.com/Gabriel-Goes/mapeamento_litologico_preditivo/tree/main/source) -- Código fonte do programa Preditor Terra.

## Instalação
Siga os passos abaixo para criar um diretório e clonar o repostiório do git.
```bash
# Crie uma pasta para nosso projeto para garantir organização
mkdir -p $HOME/projetos/PreditorTerra
cd $HOME/projetos/PreditorTerra

# Clone o repositório e siga para o diretório
git clone https://github.com/Gabriel-Goes/mapeamento-litologico-preditivo.git PreditorTerra
cd PreditorTerra
```
Execute o script [intsll.sh](https://github.com/Gabriel-Goes/mapeamento-litologico-preditivo/tree/main/install.sh)
para criar um ambiente virtual com [venv](https://docs.python.org/3/library/venv.html).  
```
# Habilitando modo execução do arquivo
chmod +x ./install.sh
./install.sh
```
<span style="font-size:smaller;">_Este processo deve ser facilitando no futuro utilizando [docker]()_</span>

## Uso
```
./PreditorTerra
```

## Autor
Gabriel Góes

## Licença
Este projeto é licenciado sob a GPL - veja o arquivo 'LICENÇA' para detalhes.

## Contato
Para mais informações, entre em contato pelo correio eletrônico gabrielgoes@usp.br

## Contribuições

Para Contribuir com este projeto basta enviar um pull request.
Será adicionado neste arquivo uma lista de frentes a serem desenvolvidas e necessitam de contribuição.

#### Contribuições de:

 - Hilo Góes

#### Apoio de:
 - Dr. Caetano Juliani
 - Victor S. Silva
 - Luiz Dutra
 - Rodrigo Brust
 - Vinicius A. Louro
