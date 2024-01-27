# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
#
# # ------------------------------ IMPORTS ------------------------------------
import pandas as pd
import fiona
from shapely.geometry import shape
from tqdm import tqdm
import pyproj
from shapely.ops import transform
from verde import inside


from utils import set_gdb


# ------------------------------ CLASSES ------------------------------------
class ManipularMalhaCartografica:
    def __init__(self, escala='50k', arquivo_geopackage=None):
        self.escala = escala
        self.arquivo_geopackage = set_gdb(arquivo_geopackage)
        self.malha_cartografica = self.importar_malha_cartografica(escala)

    def importar_malha_cartografica(self, escala='50k'):
        # Abre a camada do geopackage com fiona
        with fiona.open(self.arquivo_geopackage,
                        'r', layer=escala,
                        encoding='utf-8') as layer:
            # Converte os dados geopackage para um DataFrame do Pandas
            records = [feature for feature in layer]
            df = pd.DataFrame.from_records(records)
            # Converte a geometria de cada registro para um objeto Shapely
            df['geometry'] = df['geometry'].apply(shape)

        return df

    # Método para filtrar a malha cartográfica por ID exato
    def filtrar_mc_exato(self, df, ID):
        return df[df['id'].isin(ID)]

    # Filtrar apenas ID que terminam com o padrão especificado
    def filtrar_mc_regex(self, df, ID):
        return df[df['id'].str.contais(ID + '$')]

    # Filtragem Complexa com funções Lambda
    def filtrar_mc_lambda(self, df, ID):
        return df[df['id'].apply(lambda x: x == ID or x.startswith(ID + '_'))]

    # Filtragem baseada em partes do ID
    def filtrar_mc_partes(self, df, parte_ID):
        return df[df['id'].str.startswith(parte_ID)]

    def adicionar_geofisica(self, gama_xyz=None, mag_xyz=None, extend_size=0):
        # Lógica para carregar dados geofísicos
        gama_data = pd.read_csv('/home/ggrl/database/geof/' + gama_xyz) if gama_xyz else None
        mag_data = pd.read_csv('/home/ggrl/database/geof/' + mag_xyz) if mag_xyz else None
        # Lógica para atualizar a quadricula com dados geofísicos
        list_atri = gama_data.columns
        if 'LAT_WGS' in list_atri:
            gama_data.rename(columns={'LAT_WGS': 'LATITUDE',
                                      'LONG_WGS': 'LONGITUDE'},
                             inplace=True)
        if 'eTH' in list_atri:
            gama_data.rename(columns={'eTH': 'eTh'},
                             inplace=True)
        list_atri = mag_data.columns
        if 'LAT_WGS' in list_atri:
            mag_data.rename(columns={'LAT_WGS': 'LATITUDE',
                                     'LONG_WGS': 'LONGITUDE'},
                            inplace=True)

        gama_coords = (gama_data.X, gama_data.Y)
        mag_coords = (mag_data.X, mag_data.Y)
        wgs84 = pyproj.CRS('EPSG:4326')
        ids = list(self.malha_cartografica.keys())
        gama_df = pd.DataFrame()
        mag_df = pd.DataFrame()
        for id in tqdm(ids):
            utm = pyproj.CRS('EPSG:'+self.malha_cartografica[id]['folha']['EPSG'])
            carta_wgs84 = self.malha_cartografica[id]['folha']['geometry']
            project = pyproj.Transformer.from_crs(wgs84,
                                                  utm,
                                                  always_xy=True).transform
            carta_utm = transform(project, carta_wgs84)
            region_utm = carta_utm.bounds
            reg = (region_utm[0]-extend_size, region_utm[2]+extend_size,
                   region_utm[1]-extend_size, region_utm[3]+extend_size)
            if gama_xyz:
                gama = gama_data[inside(gama_coords, reg)]
                if len(gama) > 1000:
                    self.malha_cartografica[id].update({gama_xyz: gama})
                    gama_df = pd.concat([gama, gama_df])
                    print(f' - {gama_xyz} atualizado na folha: {id} com {len(gama_df)} pontos')
            if mag_xyz:
                mag = mag_data[inside(mag_coords, reg)]
                if len(mag) > 1000:
                    self.malha_cartografica[id].update({mag_xyz: mag})
                    mag_df = pd.concat([mag, mag_df])
                    print(f' - {mag_xyz} atualizado na folha: {id} com {len(mag_df)} pontos')

        return gama_df, mag_df

    def adicionar_litologia(self, camada=None):
        # Lógica para adicionar informações de litologia à quadricula

    def remover_quadriculas_sem_dados(self):
        # Lógica para remover quadriculas sem dados
        for id in tqdm(list(self.malha_cartografica.keys())):
            columns = list(self.malha_cartografica[id].keys())
            # Caso a quadricula tenha apenas a geometria e o id ela é removida
            if len(self.malha_cartografica[id]) <= 2:
                self.malha_cartografica.pop(id)
            # Caso a quadricula possua menos de 5000 pontos ela é removida
            # REVISÃO
            elif len(self.malha_cartografica[id][columns[2]]) < 5000:
                self.malha_cartografica.pop(id)
        return self.malha_cartografica

    def salvar_quadricula(self, nome_arquivo_saida):
        # Lógica para salvar a quadricula atualizada em um arquivo
        pass

    # Outros métodos úteis podem ser adicionados aqui conforme necessário
