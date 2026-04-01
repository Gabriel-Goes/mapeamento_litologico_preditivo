# Mensagem para Gamba (2026-03-05)

Fala, Gamba, tudo bem?

Fechamos um MVP funcional no PreditorTerra para planejamento territorial no QGIS e consolidamos as evidências técnicas.

## O que já está entregue

- Fluxo ponta a ponta por folha: banco -> interpolação -> SOM -> mapa preditivo.
- Fluxo territorial acoplado ao SOM com score multicritério transparente.
- Camadas finais no QGIS: `PT_POTENCIAL`, `PT_RESTRICOES`, `PT_PRIORIDADE`.
- Persistência de execução em `ml.run` e relatório técnico JSON por folha.

## Status técnico desta entrega

- Triagem dedicada: blocking=0, major=0, minor=74
- Gates: som_success=True, territorial_success=True
- Dossiê técnico: `docs/gamba/entrega_mvp_2026-03-05.md`

## O que precisamos de vocês para a próxima rodada

1. 1-2 relatórios multicritério anteriores (PDF).
2. Tabela de critérios e pesos usados hoje.
3. Camadas GIS de restrições/condicionantes do planejamento territorial.
4. Um caso piloto prioritário (folha/área + data de referência).
5. Se possível, um relatório em andamento para comparação lado a lado.

Com isso, fazemos a réplica metodológica e validamos o protótipo contra o fluxo atual de vocês.
