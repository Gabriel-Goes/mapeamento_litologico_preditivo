import geopandas as gpd
import pandas as pd

gdb = '/home/ggrl/geodatabase/' # DEFININDO CAMINHO PARA A BASE DE DADOS
# ---------------------------------------- DEFININDO FUNÇÕES QUE LEEM OS ARQUIVOS E ARMAZENAM NA MEMORIA RAM---------------------------------------#
# IMPORTADOR DE LITOLOGIAS POR ESCALA --------------------------------------------------------------------------#
def geologico(camada, mapa=False):
    lito =  gpd.read_file(gdb+'geodatabase.gpkg',
                        driver= 'GPKG',
                        layer= camada)
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]
        if folha.empty:
            print(f"O mapa escolhido nao est'a presente na coluna MAPA da camada veotiral.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")

            return(lito)

        else:    
            return(folha)
    else:
        return(lito)


# IMPORTADOR DE DADOS AEROGEOFISICOS ---------------------------------------------------------------------------#
def geofisico(raw_data):
    geof_dataframe = pd.read_csv(gdb+'geof/'+str(raw_data))
    return geof_dataframe
