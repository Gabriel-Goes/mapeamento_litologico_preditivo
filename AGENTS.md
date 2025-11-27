# AGENTS.md
## 1. Objetivo desta etapa

Dado um **código de folha cartográfica** e uma **data de referência** (ligada ao levantamento aerogeofísico), esta etapa deve:

- Buscar cenas **ASTER** e **Sentinel-2 L2A** em catálogos STAC.
- Verificar se cada cena **cobre totalmente** a área da folha.
- Verificar se, **dentro da área da folha**, a cena é **livre de nuvens** (ou com nuvem efetivamente nula).
- Retornar as **melhores cenas ASTER e Sentinel-2** que atendam a esses critérios.

Nenhuma outra etapa (recorte, supercube, interpolação, CNN) faz parte deste fluxo.

---

## 2. Entradas

- `folha`: código da folha (ex.: `SB21_ZA_II2_NE`).
- `data_ref`: data alvo (ex.: `2008-06-01`), associada ao levantamento aerogeofísico.

Parâmetros adicionais (configuráveis, mas simples):

- `janela_aster`: intervalo de datas em torno de `data_ref` para busca ASTER.
- `janela_s2`: intervalo de datas para busca Sentinel-2.
- `catalogos_stac`: lista de endpoints STAC a serem consultados para ASTER e S2, em ordem de preferência.

---

## 3. Saídas

- Uma estrutura simples contendo:

  - Melhor cena ASTER (ou `None` se não houver nenhuma válida).
  - Melhor cena Sentinel-2 (ou `None` se não houver nenhuma válida).
  - Opcionalmente: lista de candidatos aprovados (sem nuvem e com cobertura total) para diagnóstico.

Cada cena deve trazer, no mínimo:

- identificador (`collection`, `item_id`),
- data/hora da aquisição,
- distância em dias para `data_ref`,
- indicador de cobertura total da folha,
- indicador de nuvem local na folha (idealmente 0).

---

## 4. Fontes de dados

- Geometria da folha (polígono em WGS84) obtida de fonte única (BD ou arquivo).
- Catálogos STAC, por exemplo:
  - ASTER: coleções AST_L1T (e futuramente AST_07/AST_07XT em outros provedores).
  - Sentinel-2: coleção L2A (reflectância de superfície).

A lista exata de endpoints STAC é definida em configuração, não nesta lógica.

---

## 5. Lógica geral – ASTER

1. Obter a geometria da folha em WGS84 e seu bbox.
2. Buscar cenas ASTER em catálogos STAC:

   - Usar `intersects = geometria_da_folha`.
   - Restringir pela `janela_aster` em torno de `data_ref`.
   - Opcional: filtrar por nebulosidade global (`eo:cloud_cover`) se existir.

3. Para cada cena candidata:

   - Identificar um asset de imagem principal (TIF adequado).
   - Recortar a imagem para a área da folha (ou usar máscara sobre o bbox).
   - Calcular:

     - se toda a área da folha está coberta por pixels válidos (cobertura total),
     - fração de pixels nodata na folha,
     - fração de pixels de nuvem na folha (quando houver informação suficiente para isso).

4. Rejeitar qualquer cena ASTER que:

   - não cubra totalmente a folha,
   - tenha qualquer fração significativa de nuvem na folha (para esta etapa, alvo é nuvem zero),
   - tenha nodata afetando a cobertura da folha.

5. Entre as cenas restantes (sem nuvem e com cobertura total):

   - Ordenar pela distância temporal a `data_ref` (|data_cena – data_ref|).
   - Escolher a primeira como **melhor ASTER**.
   - Manter as demais aprovadas como candidatas adicionais (opcional).

---

## 6. Lógica geral – Sentinel-2

1. Usar a mesma geometria da folha em WGS84.
2. Buscar cenas Sentinel-2 L2A em catálogos STAC:

   - `intersects = geometria_da_folha`.
   - Restringir pela `janela_s2` (definida em configuração; pode ser relativa a `data_ref` ou à data da ASTER selecionada).
   - Usar `eo:cloud_cover` apenas como filtro inicial simples (por exemplo, descartar cenas com nuvem global extremamente alta).

3. Para cada cena candidata:

   - Identificar assets das bandas óticas e da camada de classificação de cena (SCL) ou equivalente.
   - Recortar a SCL (ou máscara de nuvem equivalente) para a área da folha.
   - Calcular:

     - se toda a área da folha está coberta por SCL/dados válidos,
     - fração de pixels classificados como nuvem na folha,
     - fração de pixels nodata na folha.

4. Rejeitar qualquer cena Sentinel-2 que:

   - não cubra totalmente a folha,
   - tenha qualquer nuvem dentro da folha (para esta etapa, alvo é nuvem zero),
   - tenha nodata prejudicando a cobertura da folha.

5. Entre as cenas restantes (sem nuvem e com cobertura total):

   - Ordenar pela distância temporal (em relação a `data_ref` ou à data da ASTER, conforme definido).
   - Escolher a primeira como **melhor Sentinel-2**.
   - Manter as demais aprovadas como candidatas adicionais (opcional).

---

## 7. Comportamento em casos sem cenas perfeitas

Se **nenhuma** cena ASTER ou Sentinel-2 atender a:

- cobertura total da folha,
- nuvem zero,

então:

- A etapa deve retornar explicitamente que **não há cena ideal**, junto com:
  - lista ordenada de cenas “menos ruins” (por exemplo, menor nuvem local, mesmo que > 0),
  - métricas de nuvem e cobertura para cada uma.

A lógica de aceitar ou não essas cenas “menos ideais” é responsabilidade de etapas posteriores ou de decisão manual, não desta especificação.

---

## 8. Escopo restrito

- Esta etapa **não** executa:
  - recorte definitivo para supercube,
  - reamostragem,
  - interpolação geofísica,
  - extração de patches,
  - treinamento de modelos.

- O único objetivo é: dado `folha` + `data_ref`, retornar as melhores imagens ASTER e Sentinel-2 que cubram totalmente a folha e sejam livres de nuvem na área da folha, ou indicar claramente que isso não foi possível.

