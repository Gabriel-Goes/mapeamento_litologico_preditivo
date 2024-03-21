# Preditor Terra

## Sobre o Projeto

Projeto que visa a produção de um sistema dinâmico de produção de mapas
preditivos, no qual, ao se disponibilizar novos dados, novas predições serão
geradas.


@startuml PreditorTerra
title Integração de Dados Geológicos e Modelos de IA
!define osaPuml https://raw.githubusercontent.com/Crashedmind/PlantUML-opensecurityarchitecture2-icons/master
!include <osa/user/audit/audit.puml>
!theme plain
allowmixing

' Definição de Componentes
' Processo de Validação
package "Geocientistas" {
    entity "Validação e Análise\npor Especialistas" as validacao {
        <$audit{scale=0.25}>  Geocientista
      +ValidarResultados(): Boolean
      +AnalisarPrecisão(): Double
    }
    entity "Dados" as dados {
        -Localização: Coordenadas
        -Dados Geológicos : String
        -Dados Geoquímicos: Double
        -Dados Geofísicos : Double
    }
}


database "PostgreSQL\\\n   PostGIS" as banco {
}
package "Gestão de Dados" {
    entity "Articulação de\n Folhas Cartográficas" as articulacao {
      +DefinirEstrutura(): void
      +PadronizarDados(): void
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
    sprite $pedaco [41x100/16] {
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    0000000000000000000FCBCCCCCCDDCCCCCCCCF00
    0000000000000000000FA8997899AA9989879AF00
    0000000000000000000FA8798899A88998999AF00
    0000000000000000000F97798898A87999999AF00
    0000000000000000000F889988998969999899F00
    0000000000000000000F979989887A6899899AF00
    0000000000000000000F87988866786899699AF00
    0000000000000000000F87899666896899689AF00
    0000000000000000000F87799876986799899AF00
    0000000000000000000FBAABBBA9AA9AABBBBBF00
    0000000000000000000F98896766786888899AF00
    0000000000000000000F98796666786888899AF00
    0000000000000000000F98896666786888999AF00
    0000000000000000000F98776566787888999AF00
    0000000000000000000F98556566786888999AF00
    0000000000000000000F96456566786899999AF00
    0000000000000000000F96456566786999999AF00
    0000000000000000000F87766666786899999AF00
    0000000000000000000FAAA99999AA9ABBBBBBF00
    0000000000000000000F78656656786799999AF00
    0000000000000000000F78665555786799999AF00
    0000000000000000000F87776665786799999AF00
    0000000000000000000F78776666786799999AF00
    0000000000000000000F58766665786799999AF00
    0000000000000000000F46876665786699999AF00
    0000000000000000000F54887655786699999AF00
    0000000000000000000F44688665786689999AF00
    0000000000000000000F878AAA99AA99ABBBBBF00
    0000000000000000000F54478876786689999AF00
    0000000000000000000F53368876786679999AF00
    0000000000000000000F53478876786679999AF00
    0000000000000000000F64368776786679999AF00
    0000000000000000000F64358886786679999AF00
    0000000000000000000F63347887786679999AF00
    0000000000000000000F53336887786656999AF00
    0000000000000000000F53336877786556999AF00
    0000000000000000000F87778AA99A8889BBBBF00
    0000000000000000000F55556997887778AAAAF00
    0000000000000000000F44456886786669999AF00
    0000000000000000000F44356766786689999AF00
    0000000000000000000F44357766786699999AF00
    0000000000000000000F43458666786899999AF00
    0000000000000000000F43566666786999999AF00
    0000000000000000000F44566666786999999AF00
    0000000000000000000F555666668879999999F00
    0000000000FFFFFFFFFF778888889BAAAAAAA9F00
    0000000000F9999755588888888899AAAAAA97F00
    0000000000F887543347766666667999999956F00
    0000000000F743344457766666668A99999656F00
    0000000000E33444555876666666AA99997556F00
    0000000000E55555556876666669AA99985568F00
    0000000000E55555566876666799AA99965558F00
    0000000000E55555666876668999AA99855556F00
    0000000000E45556666876689899AA99655556F00
    0FFFFFFFFFF566677778879AAAAABBA9766666F00
    0E76568866978888899A98BBBBBABFFFFFFFFFF00
    0E54245533745566666865999997AF00000000000
    0D54245433755666666765899997AF00000000000
    0D53355443755666665767998888AF00000000000
    0E53444533755666665769996975AF00000000000
    0D464334437666666657799857977F00000000000
    0D465434547666666657689856887F00000000000
    0E888643558666666557699967898F00000000000
    0E88864444776666665899999999AF00000000000
    0E9AA87788A99999988AFEEEEEEEEF00000000000
    0E56543443876666655AF00000000000000000000
    0E55533444976666655AF00000000000000000000
    0E554334449766666659F00000000000000000000
    0E53334435976666655AF00000000000000000000
    0E44334436976666659AF00000000000000000000
    0D54334446976566669AF00000000000000000000
    0D54334356975666688AF00000000000000000000
    0E44344356965666899AF00000000000000000000
    0E67777799B9999AABBCF00000000000000000000
    0D23344466866688999AF00000000000000000000
    0D33344565866777999AF00000000000000000000
    0D44344565866889999AF00000000000000000000
    0D44444655867889999AF00000000000000000000
    0D43344655867899999AF00000000000000000000
    0D44345655877899999AF00000000000000000000
    0D43345655878899999AF00000000000000000000
    0D43345655878899999AF00000000000000000000
    0E88888888BAAABBBBBBF00000000000000000000
    0D333355459888999988F00000000000000000000
    0D43335556A888999868F00000000000000000000
    0D43335667A989997668F00000000000000000000
    0D43336678A989976667F00000000000000000000
    0D43346688A989766668F00000000000000000000
    0D33356788A897666669F00000000000000000000
    0D33357888A78666667AF00000000000000000000
    0D44368878A766666569F00000000000000000000
    0E999BCBBBCBAAAAABBCF00000000000000000000
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    00000000000000000000000000000000000000000
    }
card folhas
}

artifact tabelas

' Relações Revisadas para Refletir o Novo Fluxo
validacao -r-> dados : "Coleta"
dados -d-> tabelas 
tabelas -d-> banco : "Armazena"
banco -d-> articulacao : "Estrutura"
articulacao -r-> folhas 
folhas -l> modelos: <$pedaco>
modelos -u-> mlp : "Gera"
modelos -u-> mpmp : "Gera"
mlp -u-> validacao : "Validação"
mpmp -u-> validacao : "Validação"
validacao -d-> banco : "Armazena\nAtualiza"

@enduml

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
