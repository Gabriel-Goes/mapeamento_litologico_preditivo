Preditor Territorial MVP - instalacao via ZIP

1) No QGIS: Complementos -> Gerenciar e instalar complementos.
2) Clique em "Instalar a partir de ZIP".
3) Selecione o arquivo ZIP entregue (dist/preditor_territorial_mvp_v0.1.0_gamba.zip).
4) Ative o plugin "Preditor Territorial MVP".

Uso rapido:
- Abra o painel do plugin no menu "Preditor Territorial MVP".
- Escolha a folha (padrao: SB21_ZA_II).
- Mantenha pixel em 200 m e execute "Gerar mapas territoriais".
- O plugin adiciona 3 rasters no grupo:
  Preditor Territorial MVP/Planejamento Territorial
  * PT_POTENCIAL
  * PT_RESTRICOES
  * PT_PRIORIDADE

Observacoes:
- O plugin e autonomo (nao depende de PostgreSQL).
- Dados internos no plugin: data/gamba_mvp.gpkg.
- Processamento em background (QgsTask), com botao de cancelamento.
- Ocorrencias minerais: tenta filtro de grafita; se nao houver match, usa todas as ocorrencias da folha.
