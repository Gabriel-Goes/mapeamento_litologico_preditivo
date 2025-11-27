# Plano para o projeto de mapeamento litológico preditivo

## 1. Visão geral

Queremos construir um **pipeline reprodutível** para mapeamento litológico preditivo, integrando:

* Dados aerogeofísicos (gamaespectrometria) armazenados em **PostgreSQL/PostGIS** (BD `geologia`, esquema `geof`).
* Mapeamento litológico existente (tabelas `litologia.litologia_100k`, etc.).
* Imagens orbitais **ASTER** (VNIR/SWIR, principalmente AST_L1T, AST_07, AST_07XT) e **Sentinel-2 L2A**.
* Interpolação e modelagem com **Verde** e redes neurais (CNN) em Python.

O repositório já contém módulos Python e notebooks que precisam ser **organizados, refatorados** e conectados em um fluxo único, acionado por linha de comando e utilizável em Jupyter.

---

## 2. Objetivo científico/técnico

Dado um **código de folha cartográfica** (por exemplo, `SB21_ZA_II1_NE`), queremos:

1. Selecionar cenas ASTER e Sentinel-2 apropriadas (baixa nebulosidade, proximidade temporal com o aerogama).
2. Baixar as imagens em formato COG via **STAC** (Planetary Computer e NASA LPCLOUD).
3. Recortar ASTER e S2 para a geometria dessa folha (obtida do PostGIS).
    3.1. GRAM SCHMIDT orthogonalization para alinhar ASTER VNIR/SWIR.
4. Construir um **“supercube”** ASTER+S2 (stack de bandas VNIR/SWIR e bandas relevantes de S2).
5. Integrar atributos geofísicos (ex.: `uth_razao`, `kperc_np`, etc.) e litológicos (rótulos de litologia_100k) em um conjunto de amostras.
6. Gerar **patches** de imagem (por classe) para treino de uma CNN e/ou grades interpoladas (100 m, 250 m) usando Verde.
7. Produzir saídas:

   * GeoTIFFs preditivos (mapas de probabilidade/classe litológica),
   * camadas vetoriais / rasters prontos para QGIS,
   * diagnósticos de qualidade (curvas, mapas de erro, estatísticas).

---

## 3. Requisitos técnicos

* Python 3.13 (via pyenv).
* Principais libs:

  * `pandas`, `numpy`, `xarray`, `rioxarray`, `rasterio`, `shapely`, `geopandas`.
  * `pystac-client`, `planetary_computer`, autenticadores para CMR/LPCLOUD quando necessário.
  * `psycopg2` e/ou `sqlalchemy`, `geoalchemy2`.
  * `verde`.
  * `torch` ou `tensorflow` (definir padrão e manter consistência).
* Sistema alvo: Linux (Arch / Debian), uso intenso de Jupyter.

---

## 4. Fluxo principal desejado (alto nível)

Queremos uma função/CLI principal parecida com:

```bash
python full_pipeline.py \
    --folha SB21_ZA_II2_NE \
    --aster-prefer AST_07XT \
    --aster-date-window 2008-01-01 2009-12-31 \
    --s2-date-window 2023-01-01 2023-12-31 \
    --max-cloud 20 \
    --grid-spacing 100 \
    --patch-size 32 \
    --stride 16 \
    --max-patches-per-class 2000 \
    --output-dir ./outputs/SB21_ZA_II2_NE
```

Internamente, o pipeline deve:

1. Ler parâmetros de `config.py` e sobrescrever com argumentos da CLI.
2. Consultar PostGIS:

   * pontos gamma na folha (view `geof.v_gamma_1082_corr_*`),
   * litologias (`litologia.litologia_100k`),
   * geometrias das folhas (tabela `folhas_cartograficas` ou equivalente).
3. Buscar ASTER:

   * Tentar **AST_07XT** (reflectância) em LPCLOUD; se não houver, cair para AST_07; se ainda assim falhar, usar AST_L1T em Planetary Computer.
   * Escolher cena com melhor combinação de cobertura da folha, nebulosidade e proximidade da data alvo (aerogama).
4. Buscar Sentinel-2 L2A:

   * Selecionar cena(s) com baixa nebulosidade e boa cobertura da folha.
5. Baixar e recortar:

   * ASTER e S2 recortados para a folha e reprojetados para a mesma grade.
   * Criar supercube ASTER+S2, com bandas padronizadas.
6. Interpolação:

   * Usar Verde para gerar grids de 100 m das variáveis gama e/ou atributos derivados (p.ex. `uth_razao`, `kperc_np`).
7. Preparação de dados para CNN:

   * Combinar supercube + grids interpolados + rótulos litológicos em patches.
   * Balancear patches entre classes (definido por `max_patches_per_class`).
8. Treino/validação:

   * Treinar CNN (config padrão + possibilidade de override).
   * Salvar pesos do modelo e métricas.
9. Inferência:

   * Aplicar modelo treinado para toda a folha, gerar mapas GeoTIFF.
10. Export:

    * Salvar outputs em diretório organizado por folha.
    * Opcional: gravar resultados em tabelas PostGIS.

---

## 6. Tarefas prioritárias para o Codex

1. **Limpar e organizar `codes/`**

   * Identificar módulos redundantes,
   * remover funções não usadas,
   * centralizar parâmetros em `config.py`.
2. **Refatorar `full_pipeline.py`** para seguir o fluxo em 5, usando funções menores:

   * `load_folha_geometry()`
   * `select_aster_item()`
   * `select_s2_items()`
   * `download_and_clip_pair()`
   * `build_supercube()`
   * `interpolate_grids_verde()`
   * `extract_patches()`
   * `train_cnn()`
   * `run_inference()`
3. **Implementar módulos STAC** (`stac_aster.py`, `stac_s2.py`):

   * Funções capazes de buscar AST_07/AST_07XT e AST_L1T (Planetary Computer + LPCLOUD).
   * Critérios de escolha da cena (nebulosidade, cobertura da folha, distância temporal).
4. **Padronizar interpolação Verde**:

   * Um módulo genérico que recebe DataFrame com `x`, `y`, `var` e retorna grid (xarray) de 100 m, usando parâmetros de `df_knn` quando relevantes.
5. **Padronizar extração de patches**:

   * Uma única função/módulo responsável por gerar patches a partir de um array 3D (supercube) e um raster de rótulos.
6. **Infraestrutura mínima de testes**:

   * Testes simples (ex.: `pytest`) para:

     * conexão com BD e queries básicas,
     * funções STAC (mockadas ou com exemplo mínimo),
     * funções de recorte e reprojeção básica.
7. **Documentação mínima**:

   * Atualizar/crear `README.md` com:

     * descrição do fluxo,
     * dependências,
     * exemplos de execução.

---

## 7. Restrições e convenções que o Codex deve respeitar

* **Não hardcodar datas, caminhos ou credenciais** dentro dos módulos:

  * datas e folhas devem sempre vir de argumentos (CLI ou funções),
  * caminhos base e strings de conexão devem vir de `config.py` ou variáveis de ambiente.
* **Não alterar diretamente estruturas críticas do BD** (DDL, drops) sem instrução explícita:

  * acesso padrão é somente leitura nas views/tabelas já existentes.
* **Evitar duplicação de lógica** entre notebooks e `.py`:

  * se um notebook precisar de funcionalidade, ela deve existir em `codes/` e ser importada.
* **Escrever funções pequenas e reutilizáveis**:

  * fluxo grande deve ser composição de funções puras (sempre que possível).
* **Manter o código enxuto**:

  * comentários apenas quando realmente necessários,
  * evitar camadas desnecessárias de abstração.

wkt_geom	fid	id_folha	EPSG
Polygon ((-56.125 -6, -56 -6, -56 -6.125, -56.125 -6.125, -56.125 -6))	4203	SB21_ZA_II2_NE	32721
# Transform the above WKT to SW, NE coordinates
SW: (-56.125, -6.125)
NE: (-56, -6)



