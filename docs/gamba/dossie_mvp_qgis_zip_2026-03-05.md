# Dossie MVP QGIS ZIP - Preditor Territorial (2026-03-05)

## 1) Escopo desta entrega

Consolidar o ciclo completo de:

- debug do fluxo QGIS,
- estabilizacao operacional,
- empacotamento do plugin MVP em ZIP instalavel,
- contexto institucional para apresentacao com a equipe do Gamba.

Este dossie eh o documento tecnico principal da entrega atual.

## 2) Resultado final (estado atual)

- Plugin MVP territorial empacotado e pronto para instalacao via ZIP.
- Instalacao validada em ambiente Windows.
- Fluxo de geracao de mapas territoriais executando em background (`QgsTask`) com botao de cancelamento.
- Proxima etapa alinhada: apresentacao curta com equipe na semana seguinte.

## 3) Artefatos entregues

- ZIP final:
  - `dist/preditor_territorial_mvp_v0.1.0_gamba.zip`
- Hash de integridade (SHA256):
  - `b3af4a2ba536aae509ec83881745ac488ad1c39efa757ce9187b2e04424f33bd`
- GPKG interno embarcado no plugin:
  - `plugins/preditor_territorial_mvp/data/gamba_mvp.gpkg`

### 3.1 Conteudo funcional do ZIP

- Plugin `preditor_territorial_mvp`
- Motor MCDA
- Interface dock no QGIS
- Dados internos (`gamba_mvp.gpkg`)

### 3.2 Camadas internas no GPKG

- `mc_100k`: 1 feicao
- `litologia_100k`: 77 feicoes
- `ocorr_min_cprm`: 190 feicoes

## 4) Correcoes tecnicas consolidadas no ciclo

### 4.1 Estabilidade de ambiente remoto

- Ajuste de export de variaveis em scripts remotos (`set -a; source ...; set +a`) para propagacao correta de ambiente.
- Validacao de dependencias Python no precheck remoto.

### 4.2 Responsividade da interface

- Operacoes longas movidas para execucao em `QgsTask`.
- Inclusao de cancelamento de tarefa e progresso.
- Reducao de travamento total da interface durante processamento pesado.

### 4.3 Robustez de processamento territorial

- Correcao de atribuicao de restricao em areas sem litologia.
- Fallback de ocorrencias:
  - tenta filtrar grafita,
  - se nao houver match por atributo, usa ocorrencias minerais da folha para manter o fluxo MVP operacional.

## 5) Evidencias de validacao

### 5.1 Testes automatizados

- `pytest -q tests/test_mvp_mcda_engine.py`
- Resultado: `2 passed`

### 5.2 Validacoes operacionais

- `bash -n scripts/build_gamba_mvp_data.sh scripts/build_qgis_plugin_mvp_zip.sh` -> OK
- Build do GPKG interno -> OK
- Build do ZIP instalavel -> OK
- Conferencia do conteudo do ZIP (`unzip -l`) -> OK

### 5.3 Evidencia de instalacao

- Instalacao validada em maquina Windows via:
  - `Complementos -> Gerenciar e instalar complementos -> Instalar a partir de ZIP`

## 6) Status institucional (Teams)

Com base em [conversas.md](/home/ggrl/projetos/PreditorTerra-terraX/docs/gamba/conversas.md):

- O novo OTGM ainda aguarda assinatura.
- Reunioes atuais estao focadas no projeto antigo.
- Gamba sinalizou interesse em agendar apresentacao da ferramenta com a equipe.
- Foi sugerido modelo de dedicacao fragmentada (participacao em reunioes SGB/ANM/SEMIL quando necessario).

## 7) Riscos e limitacoes atuais

- Cenario de folha grande (100k com muitos pontos) ainda pode ter duracao alta.
- Dependencias Python no ambiente QGIS do destinatario devem estar presentes (`geopandas`, `numpy`, `osgeo`).
- ArcMap 10.6 nao foi considerado neste ciclo por falta de validacao local.

## 8) Checklist de envio

1. Confirmar ZIP e hash.
2. Enviar mensagem objetiva com proposta de reuniao de 30 min.
3. Compartilhar guia de instalacao.
4. Coletar retorno da equipe apos smoke test.
5. Agendar calibracao de criterios e pesos com base na metodologia da SPRSF.

## 9) Proximos passos imediatos

1. Realizar apresentacao de 30 min com equipe na semana que vem.
2. Levantar criterios/camadas/pesos reais usados pela equipe.
3. Ajustar o MVP para aderencia metodologica ao fluxo multicriterio da SPRSF.
