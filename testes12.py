from qgis.core import QgsProject
import processing

# 1. Recupera as camadas pelo nome
folhas_layer = QgsProject.instance().mapLayersByName("Folhas")[0]
gamma_layer = QgsProject.instance().mapLayersByName("Gamma 1082")[0]

# 2. Verifica se há seleção na camada de folhas
selecionadas = folhas_layer.selectedFeatures()
if not selecionadas:
    raise Exception("Nenhuma folha está selecionada na camada 'Folhas'.")

# 3. Executa 'Extrair por localização' usando apenas as folhas selecionadas
params = {
    "INPUT": gamma_layer,
    "PREDICATE": [0],  # 0 = intersects
    "INTERSECT": folhas_layer,
    "METHOD": 0,       # 0 = criar nova camada apenas com as feições que cumprem o critério
    "OUTPUT": "memory:gamma_1082_folha_sel",
}

result = processing.run("native:extractbylocation", params)

layer_out = result["OUTPUT"]
layer_out.setName("Gamma 1082 - por folha selecionada")

QgsProject.instance().addMapLayer(layer_out)
