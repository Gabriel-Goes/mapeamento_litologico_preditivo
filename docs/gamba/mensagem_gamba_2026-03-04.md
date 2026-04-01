# Mensagem para Gamba (2026-03-04)

Fala, Gamba, tudo bem?

Nao esqueci do projeto. Mesmo com a carga da SOC, consegui fechar um prototipo funcional no PreditorTerra para planejamento territorial, ja rodando dentro do QGIS.

## O que ja conseguimos

- Fluxo completo por folha: banco -> interpolacao -> SOM -> mapa preditivo.
- Fluxo territorial acoplado ao SOM com score multicriterio (MCDA transparente).
- Camadas finais no QGIS (`PT_POTENCIAL`, `PT_RESTRICOES`, `PT_PRIORIDADE`).
- Relatorio tecnico JSON por folha.
- Rastreabilidade de execucao no banco (`ml.run`, com run territorial gravando id).

## O que ainda estamos fechando

- Padronizar a selecao orbital para o criterio alvo: ASTER + Sentinel-2 L2A com cobertura total da folha e nuvem local zero.
- Validacao visual final de alinhamento espacial em folha grande.

## O que preciso de voces para acelerar

1. 1-2 relatorios multicriterio anteriores (PDF).
2. Tabela de criterios e pesos que voces usam hoje.
3. Camadas GIS de restricoes/condicionantes do planejamento territorial.
4. Um caso piloto prioritario (folha/area + data de referencia).
5. Se possivel, um relatorio em andamento para comparacao lado a lado.

Com isso eu monto a replica rastreavel no plugin e a gente faz uma rodada curta de comparacao metodo atual x prototipo.

Anexo tecnico desta rodada:
- `docs/gamba/status_tecnico_gamba_2026-03-04.md`
