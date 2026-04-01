# Status Tecnico PreditorTerra para Gamba (2026-03-04)

## 1) Escopo desta consolidacao

Consolidar o estado real da branch `pesquisa/carlos-tadeu-gamba` para comunicacao externa, com evidencias verificaveis de:

- execucao SOM no QGIS,
- execucao do fluxo de prioridade territorial,
- status do modulo STAC,
- pendencias para proxima iteracao.

## 2) Evidencias mais recentes (rodada valida de 2026-03-04)

Fonte principal: `logs/sessions/qgis_run_20260304_180619.log` e `logs/preditor_terra.log`.

### 2.1 Fluxo SOM (DB -> SOM -> mapa)

- Inicio: `2026-03-04T18:06:57.909Z`
- Fim: `2026-03-04T18:07:49.803Z`
- Duracao: `51.894s`
- Folhas: `1`
- Pontos gama: `6050`
- Metricas: `QE=1.78688`, `TE=0.0505671`
- Evidencia de escrita raster:
  - `SOM raster escrito | fid=SB21_XC_IV4_SE k=8 epsg=32721 shape=(138, 138) flip_ns=False`

### 2.2 Fluxo Territorial

- Inicio de run em banco: `2026-03-04T18:09:50.090Z`
- Persistencia: `Run territorial iniciado em ml.run: id=2`
- Conclusao: `2026-03-04T18:09:50.425Z`
- Resultado: `pct_alta_media=0.150`
- Evidencia de escrita raster:
  - `Territorial raster escrito | fid=SB21_XC_IV4_SE epsg=32721 flip_ns=False shape=(138, 138)`
- Relatorio salvo:
  - `/tmp/preditor_terra_territorial/territorial_SB21_XC_IV4_SE_20260304T210950Z.json`

### 2.3 Fluxo STAC dentro do plugin

- Colecoes listadas na rodada: `7 coleção(ões)`
- Busca por AOI da folha retornou: `20 item(ns)`
- Amostragem de bandas no raster SOM:
  - `OK red`, `OK green`, `OK blue` (1 coluna cada)

### 2.4 Teste de estresse (folha grande SB21_ZA_II)

Fonte: `logs/preditor_terra.log` (janela 2026-03-04 21:56-22:08).

- Escala: `100k`
- Folhas ativas no carregamento: `2` (`SB21_ZA_II` + `SB21_ZA_III`)
- Pontos gama acumulados: `85376`
- Upload de dados: `46.025s`
- Interpolacao (`ids=1`, `feats=4`, `pixel=200m`, `linear`): `601.262s`
- Evidencia:
  - `⏱ Interpolate ids=1 feats=4 concluído (601.262s)`

### 2.5 Diagnostico remoto STAC (causa raiz confirmada)

Rodada de confirmacao (precheck) em `2026-03-04T22:22:03-03:00`:

- Antes do ajuste, havia ciclos com:
  - `PYTHONPATH (prefix): .../PreditorTerra-terraX:/codes` (sem site-packages extra)
  - `modulo ausente: pystac_client/planetary_computer/rasterio/rioxarray`
- Causa raiz:
  - `scripts/preditor_qgis.remote.env` era `source` sem exportacao; variaveis nao chegavam aos subprocessos (`run_qgis_preditor.sh`).
- Correcao aplicada:
  - `scripts/check_qgis_remote_env.sh` e `scripts/run_qgis_preditor_remote.sh` agora carregam env com `set -a; source ...; set +a`.
- Resultado apos correcao:
  - `PYTHONPATH (prefix): ...:/tmp/pt_qgis314_venv/lib/python3.14/site-packages`
  - `modulo encontrado: pystac_client/planetary_computer/rasterio/rioxarray`.

## 3) Triagem de logs (estado de envio)

Triagens de referencia:

- JSON: `logs/sessions/debug_triage_gamba_send_check_20260304T212611Z.json`
- MD: `logs/sessions/debug_triage_gamba_send_check_20260304T212611Z.md`
- Resumo:
  - `blocking=0`
  - `major=0`
  - `minor=74`
  - `som_success=True`
  - `territorial_success=True`

Triagem operacional apos ajuste de ambiente (modo `--collect-only`, sem abrir QGIS):

- JSON: `logs/sessions/debug_triage_gamba_consolidado_envfix_20260305T012203Z.json`
- MD: `logs/sessions/debug_triage_gamba_consolidado_envfix_20260305T012203Z.md`
- Resumo:
  - `blocking=0`
  - `major=0`
  - `minor=32`
  - `som_success=False` (esperado em `collect-only`)
  - `territorial_success=False` (esperado em `collect-only`)

Ruido recorrente (nao bloqueante):

- `collation_mismatch` (PostgreSQL)
- `gdal_algorithm_registered` (registro duplicado de algoritmos GDAL)

## 4) O que ja esta funcionando

- Fluxo operacional no QGIS por folha:
  - selecao de folha,
  - carga de dados geofisicos do PostGIS,
  - interpolacao,
  - SOM,
  - mapa preditivo.
- Fluxo de prioridade territorial acoplado ao SOM com MCDA e export de relatorio JSON.
- Persistencia no schema `ml.*` ativa (run territorial gravando em `ml.run`).
- Correcao aplicada para evitar escrita de raster SOM com CRS incorreto no fluxo rapido.
- Controle de `flip_ns` unificado para SOM + Territorial e logado em runtime.

## 5) Pendencias reais para a proxima rodada

### P0 - Responsividade da interface QGIS (bug de travamento)

Durante execucao de operacoes longas, a interface ficou bloqueada por rodar em `MainThread` (ex.: interpolacao da `SB21_ZA_II` com duracao de `601.262s`).

Plano aplicado nesta branch (em validacao operacional):

- migracao de `Carregar brutos`, `Interpolacao`, `Fluxo rapido` e `Prioridade territorial` para `QgsTask`,
- botao de cancelamento de operacao,
- progresso de tarefa na status bar.

Pendencia restante:

- validar em reteste guiado que o QGIS permanece utilizavel (pan/zoom/troca de abas) durante a tarefa.

### P0 - Metodologia orbital (principal)

A etapa STAC ainda precisa ser fechada para o objetivo metodologico definido no `AGENTS.md`:

- priorizar ASTER + Sentinel-2 L2A de forma explicita,
- exigir cobertura total da folha,
- exigir nuvem local nula na folha,
- retornar melhor cena e candidatos aprovados com metricas.

Observacao: em algumas consultas, os itens retornados foram Landsat 7 (`LE07...`) e sem asset `tci/visual`, o que nao atende ao criterio alvo ASTER/S2 cloud-free.

### P0 - Validacao espacial visual final

- Validar visualmente, em folha pequena e folha grande, alinhamento de:
  - raster SOM,
  - rasters territoriais,
  - base satelital de referencia.
- Foco: confirmar que nao ha espelhamento N-S residual em cenario real de uso.

### P1 - Performance para folhas grandes

- Execucoes em folhas com muitos pontos podem ficar longas.
- Precisamos fechar parametros operacionais de demo (pixel, k, atributos, limite de pontos) para garantir tempo previsivel em apresentacao.

### P1 - Higiene operacional

- Planejar manutencao de collation do banco (`ALTER DATABASE ... REFRESH COLLATION VERSION`) em janela dedicada.

### P1 - Padronizacao de ambiente STAC no remoto

- Status: **mitigado nesta rodada**.
- `PREDITOR_EXTRA_PYTHONPATH` ja definido em `scripts/preditor_qgis.remote.env`.
- Scripts remotos agora exportam automaticamente variaveis do arquivo de env.
- Proxima acao: manter `check_qgis_remote_env.sh` como gate antes de qualquer rodada orbital.

## 6) O que precisamos da equipe Gamba para avancar

Para comparar com metodologia real deles e fechar a validacao:

1. 1-2 relatorios multicriterio anteriores (PDF).
2. Tabela de criterios e pesos atuais.
3. Camadas GIS de restricoes/condicionantes usadas por eles.
4. Um caso piloto prioritario (folha/area + data de referencia).
5. Se possivel, um relatorio em andamento para comparativo lado a lado.

## 7) Conclusao executiva

A branch ja executa ponta a ponta (SOM + Territorial) com persistencia em `ml.run` e sem bloqueios criticos na triagem mais recente. O gap tecnico principal antes da mensagem final de "metodologia pronta" e fechar a selecao orbital ASTER/S2 cloud-free/full-coverage conforme especificacao, alem da validacao visual final de orientacao em folha grande.
