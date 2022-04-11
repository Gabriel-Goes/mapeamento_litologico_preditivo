# ggrl;
# geologist_machine; 
# ic_2021
\
\
\
import pandas as pd
import geopandas as gpd
import fiona
import sys
\
\
\
# ~/Geodatabase/; # ---------------------------------------------------------------------------------------------------
def gdb(path=''):
    print('')
    gdb = '/home/ggrl/geodatabase/'
    print(f' Diretório raíz: {gdb}')
    
    if path: 
        gdb += path
        print(f' Diretório do arquivo: {gdb}')

        return gdb
# ----------------------------------------------------------------------------------------------------------------------
\
\
\
# IMPORTADOR DE LITOLOGIAS POR ESCALA ---------------------------------------------------------------------------------#
def geometrias(camada, mapa=None):
    '''
    Recebe:
        camada      : camada vetorial a ser lida do geopackage.
        mapa        : nome do mapa presente na camada vetorial;
    Retorna:
        Objeto GeoDataFrame.
        
        *Se houver seleçao de mapa retornara apenas as geometrias que possuem o nome escolhido na coluna ['MAPA']
        *Se Retornar camada vazia recebera a lista das camadas veotoriais diposniveis
        *Se mapa == False: retorna todos os objetos presente nesta camada vetorial
    '''
    # Lendo camada do GeoPackage
    lito =  gpd.read_file(gdb('geodatabase.gpkg'),
            driver = 'GPKG',
            layer = camada)
    
    # Lendo mapa geológico
    if mapa:
        #print(f"Lendo Carta geológica da folha {mapa}")
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]
        print('')

        return folha
    # If none map selected, return all geometrys inside the layer
    else:
        return lito


# ----------------------------------------------------------------------------------------------------------------------

# SELECIONADOR DE REGIÃO # ---------------------------------------------------------------------------------------------
def import_malha_cartog(escala,ids=None):
    '''
    Recebe : 
        escala : 
        ids    :
        
        Retorna :
            malha_cartog_contains_id
    '''
    print(f'Lendo Malha Cartogŕafica de {escala}')
    malha_cartog = gpd.read_file(gdb('geodatabase.gpkg'),
                        driver='GPKG',
                        layer='malha_cartog_'+escala+'_wgs84') 
   
    print('')
    
    if ids:
        
        print(f'Selecionando Folhas Cartográficas que contém {ids} no id')
        malha_cartog_contains_id = malha_cartog[malha_cartog['id_folha'].str.contains(ids)] # '.contains' não é ideal.
        
        print('')

        return malha_cartog_contains_id

    else:
        return malha_cartog          



# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA ----------------------------------------------------------------------------------
def import_xyz(caminho):
    '''
    Recebe: exemplo/
    
        Retorna:
            df exemplo
    
    '''
    dataframe = pd.read_csv(caminho)

    return dataframe
# ----------------------------------------------------------------------------------------------------------------------



# IMPORTADOR DE LITOLOGIAS POR ESCALA ----------------------------------------------------------------------------------
def dado_bruto(camada, mapa,geof=None):
    '''
    Recebe:
        __camada : Camada vetorial presento no geopackage;
        __mapa   : Nome da folha cartografica presenta na coluna 'MAPA' da camada vetorial (SE NAO INSERIR MAPA RETORNA TODOS OS VETORES DA CAMADA SELECIONADA);
        __geof   : Dados dos aerolevantamentos. gama_tie, gama_line, 

    '''
    print(f'Diretório de dados aerogeofisicos brutos: {gdb(geof)}')
    geof_dataframe = import_xyz(geof)

    path_lito = gdb('geodatabase.gpkg')
    print(f'Diretório de dados litologicos brutos: {path_lito}')
    lito =  gpd.read_file(path_lito,
                        driver= 'GPKG',
                        layer= camada)
    print('')
    print(f"# -- Lista de camadas vetoriais disponiveis: {fiona.listlayers(path_lito)}")

    if lito.empty:
        raise "# FALHA : A camada escolhida nao está presente no geopackage."

    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]

        if folha.empty:
            print('')
            print("O mapa escolhido nao está presente na coluna MAPA da camada veotiral.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")

        else:    
            return folha, geof_dataframe
    else:
        return lito, geof_dataframe
# ----------------------------------------------------------------------------------------------------------------------
