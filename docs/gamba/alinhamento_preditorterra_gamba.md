# Alinhamento PreditorTerra x Gamba

## 1. Contexto

Este documento consolida o alinhamento entre o PreditorTerra e a linha de pesquisa do Carlos Tadeu de Carvalho Gamba, com foco em ordenamento territorial geomineiro, planejamento territorial minerario e suporte a decisao com SIG.

Bases consultadas no repositorio:
- `docs/gamba/pesquisas.md`
- `docs/conversas/conversas.md`
- `AGENTS.md`

## 1.1 Snapshot 2026-03-04

Documentos desta rodada (prontos para envio ao Gamba):
- `docs/gamba/mensagem_gamba_2026-03-04.md`
- `docs/gamba/status_tecnico_gamba_2026-03-04.md`

Resumo do snapshot:
- Fluxo SOM executado no QGIS com sucesso na folha `SB21_XC_IV4_SE`.
- Fluxo territorial executado com geracao de `PT_POTENCIAL`, `PT_RESTRICOES`, `PT_PRIORIDADE`.
- Persistencia `ml.*` regularizada e validada com `adaptive.cli init-db` + `run_id` territorial em `ml.run`.
- Correcao aplicada para evitar raster SOM com CRS incorreto (`EPSG:4326` com coordenadas UTM) no fluxo rapido.
- Controle de flip N-S unificado para rasters SOM + territorial (debug visual).
- STAC voltou a operar no launcher remoto padrao de demo (colecoes e itens listados).
- Infra de execucao assíncrona adicionada para operacoes longas (QgsTask + cancelamento), em fase de validacao operacional.
- Gap principal restante: fechar criterio metodologico ASTER/S2 cloud-free com cobertura total por folha.

## 2. Objetivo do Produto

Transformar o fluxo atual (folha -> dados geofisicos -> SOM -> mapa) em um produto de apoio ao planejamento territorial minerario dentro do QGIS, com rastreabilidade de execucao no PostgreSQL.

Saida-alvo por folha:
- Mapa de potencial mineral (derivado do SOM).
- Mapa de restricoes/condicionantes territoriais (hibrido opcional).
- Mapa de prioridade territorial mineraria (MCDA transparente).

## 3. Escopo MVP e Fora de Escopo

### MVP (P0)
- Fluxo por folha dentro do plugin QGIS.
- Metodo MCDA com pesos explicitados.
- Penalidade por declividade (derivada de MDT/slope).
- Restricoes opcionais por colunas disponiveis no dataset.
- Persistencia em `ml.run`, `ml.metric`, `ml.artifact`.
- Relatorio tecnico por folha em JSON.

### Fora de Escopo neste ciclo
- Modelo supervisionado para prioridade territorial.
- Pipeline em lote nacional.
- Integracao obrigatoria com todas as bases externas institucionais.
- Modulo de risco de deslizamento/enchente.

## 4. Arquitetura Alvo

### Entrada
- Folha cartografica selecionada no plugin.
- Data de referencia (`data_ref`) para consulta orbital ASTER/S2.
- Dados geofisicos da folha via PostGIS (`carto`, `geof`).

### Processamento
1. Fluxo rapido DB -> SOM -> Mapa preditivo (existente).
2. Conversao de classes SOM para score de potencial via medianas normalizadas e pesos.
3. Aplicacao de mascaras:
- hard constraint (restricao territorial opcional).
- soft constraint (declividade).
4. Geracao de score final e classes de prioridade.

### Saida
- Rasters no QGIS:
- `PT_POTENCIAL_{folha}`
- `PT_RESTRICOES_{folha}`
- `PT_PRIORIDADE_{folha}`
- Relatorio JSON por folha.
- Registro da execucao no banco (`ml.*`).

## 5. Backlog Tecnico (P0/P1/P2)

## P0 - Vertical slice funcional
- [x] Documento de alinhamento e backlog no repositorio.
- [x] Modulo `codes/territorial_priority.py` (MCDA transparente).
- [x] Modulo `codes/territorial_sources.py` (mascaras hibridas opcionais).
- [x] Integracao no plugin QGIS com aba/bloco de prioridade territorial.
- [x] Geracao das 3 camadas territoriais no canvas.
- [x] Persistencia `ml.run` + metricas + artefatos.
- [x] Relatorio JSON por folha com parametros e metricas.
- [x] Migracao de operacoes longas para `QgsTask`:
- `Carregar brutos`, `Interpolacao`, `Fluxo rapido`, `Prioridade territorial`.
- [x] Botao de cancelamento de operacao longa no dock.

## P1 - Robustez operacional
- [ ] Parametrizacao por interface (pesos, limiares, penalidade).
- [ ] Logging estruturado por execucao.
- [ ] Tratamento padrao de ausencia de cenas orbitais ideais.
- [ ] Validacao de qualidade por folha (completude de colunas e cobertura).
- [x] Padronizar ambiente STAC remoto (`PREDITOR_EXTRA_PYTHONPATH`) e exportacao automatica no launcher remoto.

## P2 - Escala e governanca
- [ ] Lote por multiplas folhas.
- [ ] Comparacao temporal de runs (`ml.run_compare`).
- [ ] Relatorio tecnico em formato padrao para planejamento territorial.

## 6. Criterios de Aceite

Um run e considerado aceito quando:
1. Usuario seleciona folha e executa no plugin sem erro bloqueante.
2. Sistema gera as camadas `PT_POTENCIAL`, `PT_RESTRICOES`, `PT_PRIORIDADE`.
3. Sistema grava um registro em `ml.run` com status final.
4. Sistema grava metricas e artefatos associados ao `run_id`.
5. Relatorio final explicita pesos, limiares, fontes e resultado por folha.

## 7. Riscos e Mitigacao

- Dependencia de dados de restricao territorial incompletos.
- Mitigacao: estrategia hibrida opcional, sem bloquear o fluxo principal.

- Variabilidade de ambiente Python do QGIS.
- Mitigacao: imports tolerantes a falha e degradacao controlada.

- Falha de conectividade com catalogos STAC.
- Mitigacao: registrar no relatorio como aviso e seguir com fluxo local.

## 8. Checklist de Implementacao

### Codigos
- [x] Criar `codes/territorial_priority.py`.
- [x] Criar `codes/territorial_sources.py`.
- [x] Integrar novo fluxo no `codes/PreditoTerra_QGIS.py`.
- [x] Registrar run no `ml.*` com status e metricas.
- [x] Exportar relatorio JSON por folha.

### Plugin QGIS
- [x] Adicionar controles de `data_ref`, limiares e penalidade.
- [x] Adicionar botao `Gerar Prioridade Territorial`.
- [x] Renderizar rasters no grupo `Preditor Terra/Planejamento Territorial`.

### Validacao
- [x] Rodar validacao estatica (import/compilacao).
- [x] Executar fluxo de demonstracao em uma folha piloto.
- [x] Conferir persistencia no Postgres.
- [ ] Validar responsividade da UI durante execucao longa (sem congelamento geral).
- [ ] Fechar reteste visual de orientacao SOM/territorial versus base satelital apos correcoes.
