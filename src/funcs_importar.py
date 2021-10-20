# ggrl;
# geologist_machine; 
# ic_2021
\
\
\

import pandas as pd
import geopandas as gpd
import fiona


# ~/Geodatabase/; # ---------------------------------------------------------------------------------------------------
def gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/geodatabase/'

        path : caminho até o arquivo desejado
    '''
    gdb = '/home/ggrl/geodatabase/' + path
    return gdb
# ----------------------------------------------------------------------------------------------------------------------


class Import:
    '''

    '''
    # Params -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def __init__(self,caminho,usecols,layer):
        self.caminho = caminho
        self.usecols = usecols
        self.layer = layer
    # --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    # Gama ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def gama(self):
        '''

        '''

        df = pd.read_csv(gdb(self.caminho),
                            usecols = self.usecols)
                                
        return df
    # --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    # Mag ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def mag(self):
        '''
        
        '''

        df = pd.read_csv(gdb(self.caminho),
                        usecols = self.usecols)

        return df


    def litologia(self):
        '''
        
        '''
        litologia = gpd.read_file(gdb('geodatabase.gpkg'),
                                      driver='GPKG',
                                      layer=self.layer)

        return litologia

    def malha_cartog(self):
        '''
        
        '''
        malha_cartog = gpd.read_file(gdb('geodatabase.gpkg'),
                                     driver = 'GPKG',
                                     layer  = self.layer)

        return malha_cartog

    # SELECIONADOR DE REGIÃO # ---------------------------------------------------------------------------------------------
    def import_malha_cartog(escala,ids):

        malha_cartog = gpd.read_file(gdb('geodatabase.gpkg'),
                                    driver='GPKG',
                                    layer='malha_cartog_'+escala+'_wgs84')

        malha_cartog_id_select = malha_cartog[malha_cartog['id_folha'].str.contains(ids)] # '.contains' não é ideal.
        
        return malha_cartog_id_select
    # ----------------------------------------------------------------------------------------------------------------------

    # IMPORTADOR DE LITOLOGIAS POR ESCALA ----------------------------------------------------------------------------------
    def import_xyz(caminho):
        '''
        
        '''
        dataframe = pd.read_csv(caminho,
                                names='KB DATA BARO UB THB COSMICO CTB UUP ALTURA KPERC eU eTH CTEXP UTHRAZAO X Y UKRAZAO MDT THKRAZAO LIVE_TIME CTCOR KCOR THCOR UCOR HORA GPSALT LATITUDE FIDUCIAL TEMP LONGITUDE'.split(" "),
                                delim_whitespace=True,
                                skiprows=11,                                     # Linhas de cabeçalho
                                usecols=['X','Y','LATITUDE','LONGITUDE','KPERC','eU','eTH','CTCOR','MDT'])

        dataframe.dropna(inplace=True)

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
        geof_dataframe = Import().import_xyz(geof)

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
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------