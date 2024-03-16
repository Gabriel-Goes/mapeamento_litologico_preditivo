# Projeto: Mapeamento Litológico Preditivo

## Preditor Terra

### Autor
Gabriel Góes

### Correio eletrônico
gabrielgoes@usp.br

### Licença
GPL

## Sobre o Projeto
Projeto que visa a produção de um sistema dinâmico de produção de mapas preditivos,
no qual, ao se disponibilizar novos dados, novas predições serão geradas.

@startuml PreditorTerra
title Integração de Dados Geológicos e Modelos de IA
!theme plain

' Definição de Componentes
package "Dados" {
    entity "Dados Geológicos" as dados {
      -Localização: Coordenadas
      -Dados Categórigos: String
      -Dados Numéricos: Double
    }
}

package "Banco de Dados" {
    entity "PostgreSQL/PostGIS" as banco {
      +AdicionarDados(): void
      +AtualizarDados(): void
      +ConsultarDados(): List
    }
}

package "Análise de Dados" {
    entity "Modelos de IA" as modelos {
      -Supervisionado: String
      -Agrupamento: String
      +TreinarModelos(): void
      +TestarModelos(): void
    }
    entity "MPM Preditivos" as mpmp {
      -Prob. de Ocorrência: Double
      -Precisão: Double
    }
    entity "Mapas Litológicos Preditivos" as mlp {
      -Classes Litológicas: List
      -Precisão: Double
    }
}

package "Gestão de Dados" {
    entity "Articulação de Folhas Cartográficas" as articulacao {
      +DefinirEstrutura(): void
      +PadronizarDados(): void
    }

}

' Processo de Validação
package "Geocientistas" {
    entity "Validação e Análise\npor Especialistas" as validacao {
      +ValidarResultados(): Boolean
      +AnalisarPrecisão(): Double
    }
}

' Relações Revisadas para Refletir o Novo Fluxo
dados -d-> banco : "armazena"
banco -d-> articulacao : "estrutura"
articulacao -r-> modelos : "alimenta"
modelos -u-> mlp : "gera"
modelos -u-> mpmp : "gera"
mlp -u-> validacao : "validação"
mpmp -u-> validacao : "validação"
validacao -d-> banco : "atualiza"

@enduml

## Instalação
```bash
git clone https://github.com/Gabriel-Goes/mapeamento-litologico-preditivo.git
cd mapeamento-litologico-preditivo
```

## Uso

## Estrutura do Projeto
O Projeto está estrutura em 4 caminhos principais:
    - docs
    - dotfiles
    - jupyternotebooks
    - source

Em docs teremos os documentos que fornecem informações sobre o projeto, assim
como relatórios de pesquisa.

Em dotfiles teremos arquivos de configuração do ambiente de programação, como
o environment.yml que serve para configurar o ambiente virutal do python, o arquivo
zettlevim.lua que servirá para configurar funcionalidades que simulam o zettelkasten
no ambiente da interface de desenvolvimento [Neovim](https://neovim.io/) assim como
outros arquivos de configuração deste ambiente de desenvolvimento.

Em jupyternotebooks temos os scripts de tutoriais e teste de código.

Em source teremos o código fonte do programa Preditor Terra.

```
  docs
    GPT
    images
    jupyternotebooks
    posters
    projetos
    relatorios
    resumos
    uml
  dotfiles
  jupyternotebooks
  source
   README.md   # Você está aqui!
```

## Licença
Este projeto é licenciado sob a GPL - veja o arquivo 'LICENÇA' para detalhes.

## Contato
Para mais informações, entre em contato pelo correio eletrônico gabrielgoes@usp.br

## Contribuição

Para Contribuir com este projeto basta enviar um pull request.
Será adicionado neste arquivo uma lista de frentes a serem desenvolvidas e necessitam de contribuição.

#### Contribuições de:

 - Hilo Góes

#### Apoio de:
 - 
 - Victor S. Silva
 - Luiz Dutra
 - Rodrigo Brust
 - Vinicius A. Louro
