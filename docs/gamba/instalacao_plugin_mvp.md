# Instalacao do Plugin MVP (ZIP)

## Artefato de entrega

- Arquivo ZIP: `dist/preditor_territorial_mvp_v0.1.0_gamba.zip`
- Plugin interno: `preditor_territorial_mvp`
- Dados internos embarcados: `data/gamba_mvp.gpkg`
- Recorte atual embarcado (folha `SB21_ZA_II`):
  - `mc_100k`: 1 feicao
  - `litologia_100k`: 77 feicoes
  - `ocorr_min_cprm`: 190 feicoes

## Como instalar no QGIS

1. Abrir `Complementos -> Gerenciar e instalar complementos...`
2. Ir em `Instalar a partir de ZIP`.
3. Selecionar `preditor_territorial_mvp_v0.1.0_gamba.zip`.
4. Confirmar e habilitar o complemento `Preditor Territorial MVP`.

## Transferencia do ZIP para Windows (SSH)

## rsync (porta + chave corretas)

```bash
rsync -avP -e "ssh -p 62222 -i ~/.ssh/ipt_ed25519" \
  ggrl@geodb.duckdns.org:/home/ggrl/projetos/PreditorTerra-terraX/dist/preditor_territorial_mvp_v0.1.0_gamba.zip \
  ./
```

## scp (alternativa simples)

```bash
scp -P 62222 -i ~/.ssh/ipt_ed25519 \
  ggrl@geodb.duckdns.org:/home/ggrl/projetos/PreditorTerra-terraX/dist/preditor_territorial_mvp_v0.1.0_gamba.zip \
  ./
```

## Integridade do arquivo

```bash
sha256sum preditor_territorial_mvp_v0.1.0_gamba.zip
# esperado: b3af4a2ba536aae509ec83881745ac488ad1c39efa757ce9187b2e04424f33bd
```

## Como executar

1. Abrir o painel em `Preditor Territorial MVP -> Abrir Preditor Territorial MVP`.
2. Selecionar a folha.
3. Ajustar `Pixel (m)` e limiares (medio/alto).
4. Clicar em `Gerar mapas territoriais`.

## Smoke test recomendado

1. Abrir plugin, selecionar folha e iniciar processamento.
2. Confirmar que a interface permanece utilizavel durante a execucao.
3. Confirmar criacao do grupo `Preditor Territorial MVP/Planejamento Territorial`.
4. Confirmar presenca das camadas:
- `PT_POTENCIAL`
- `PT_RESTRICOES`
- `PT_PRIORIDADE`
5. Confirmar arquivo de relatorio em:
- `%TEMP%\\preditor_territorial_mvp\\PT_RELATORIO_*.json`

## Saidas produzidas

- Grupo no QGIS:
  - `Preditor Territorial MVP/Planejamento Territorial`
- Rasters:
  - `PT_POTENCIAL`
  - `PT_RESTRICOES`
  - `PT_PRIORIDADE`
- Arquivos em disco:
  - `/tmp/preditor_territorial_mvp/PT_*.tif`
  - `/tmp/preditor_territorial_mvp/PT_RELATORIO_*.json`

## Observacoes tecnicas

- O plugin nao depende de PostgreSQL.
- Dependencias Python no ambiente QGIS: `geopandas`, `numpy`, `osgeo` (GDAL).
- A execucao roda em `QgsTask` (background), com botao de cancelamento.
- Camadas obrigatorias no GPKG interno:
  - `mc_100k`
  - `litologia_100k`
  - `ocorr_min_cprm`

## Troubleshooting rapido

- Plugin nao aparece na lista:
  - reiniciar o QGIS apos instalacao do ZIP.
- Erro de import Python:
  - validar no console Python do QGIS:
  - `import geopandas, numpy, osgeo`
- Camada nao gerada:
  - verificar permissao de escrita em `%TEMP%`.
