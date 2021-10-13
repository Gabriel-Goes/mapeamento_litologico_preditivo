import geopandas as gpd
import pandas as pd
import fiona

 # DEFININDO CAMINHO PARA A BASE DE DADOS

# IMPORTADOR DE LITOLOGIAS POR ESCALA --------------------------------------------------------------------------#
def geometrias(camada=False, mapa=False, geofisico=False):
    '''
    Recebe:
        camada: Camada vetorial presento no geopackage
        mapa  : Nome da folha cartografica presenta na coluna 'MAPA' da camada vetorial
        (SE NAO INSERIR MAPA RETORNA TODOS OS VETORES DA CAMADA SELECIONADA)

    '''
    gdb      = '/home/ggrl/geodatabase/'
    geof_gdb = gdb+'geof/'

    if geofisico:
        geof_dataframe = pd.read_csv(geof_gdb+geofisico)

        return geof_dataframe
        
    if camada:
        lito =  gpd.read_file(gdb+'geodatabase.gpkg',
                            driver= 'GPKG',
                            layer= camada)

        if lito.empty:
            print(f"A camada escolhida nao est'a presente no geopackage.")
            print(f"# -- Lista de camadas vetoriais disponiveis: {list(fiona.listlayers(gdb+'geodatabase.gpkg'))}")
            return lito

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