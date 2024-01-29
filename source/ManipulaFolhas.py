# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Esta classe é responsável por manipular as folhas de cartas.
# Adicionando dados geofísicos, litologia e removendo folhas sem dados.
#
# # ------------------------------ IMPORTS ------------------------------------
import pandas as pd
from tqdm import tqdm
import pyproj
from shapely.ops import transform
from verde import inside

from geologist.utils.utils import set_gdb


# ------------------------------ CLASSES ------------------------------------
class ManipularFolhas:
    def __init__(self, dicionario_folha):
        '''
        Esta classe é responsável por manipular as folhas de cartas.
        Adicionando dados geofísicos, litologia e removendo folhas sem dados.

        Sintaxe:
        ManipularFolhas(dicionario_folha)

        Parâmetros:

        Exemplo:

        '''
        self.folhas = dicionario_folha

    # Método para recortar dados geofísicos de acordo com a bbox da folha e
    # adicionar à folha
    def selecionar_dados_geofisicos(self, dados, tipo, extend_size=0):
        '''
        Este método seleciona os dados geofísicos de acordo com a bbox da folha
        e adiciona à folha.

        Sintaxe:
        selecionar_dados_geofisicos(dados, tipo, extend_size=0)

        Parâmetros:
        dados: DataFrame com os dados geofísicos
        tipo: tipo de dado geofísico (gama_xyz ou mag_xyz)
        extend_size: tamanho da extensão da bbox da folha

        '''
        # Lógica para selecionar dados geofísicos
        wgs84 = pyproj.CRS('EPSG:4326')
        # iterar sobre as folhas
        dados_folha_list = []
        for id, folha in tqdm(self.folhas.items()):
            # se id contem SF23, printar
            # transformar a folha para utm
            utm = pyproj.CRS('EPSG:' + folha['EPSG'])
            project = pyproj.Transformer.from_crs(wgs84,
                                                  utm,
                                                  always_xy=True).transform
            folha_utm = transform(project, folha['geometry'])
            region_utm = folha_utm.bounds
            reg = (region_utm[0] - extend_size, region_utm[2] + extend_size,
                   region_utm[1] - extend_size, region_utm[3] + extend_size)
            # selecionar dados geofísicos
            dados_folha = dados[inside((dados.X, dados.Y), reg)]
            # adicionar dados geofísicos à folha
            if len(dados_folha) > 1000:
                self.folhas[id].update({tipo: dados_folha})
                dados_folha_list.append(dados_folha)
            else:
                pass
        if len(dados_folha_list) > 0:
            df = pd.concat(dados_folha_list)

            return df

    # Método para carregar e selecionar dados geofísicos
    def carregar_e_selecionar_geofisica(self, arquivo_xyz, tipo, extend_size):
        '''
        Este método carrega e seleciona dados geofísicos de acordo com a bbox
        da folha e adiciona à folha.

        Sintaxe:
        carregar_e_selecionar_geofisica(arquivo_xyz, tipo, extend_size)

        Parâmetros:
        arquivo_xyz: nome do arquivo xyz
        tipo: tipo de dado geofísico (gama_xyz ou mag_xyz)
        extend_size: tamanho da extensão da bbox da folha

        '''
        if arquivo_xyz is None:
            # Retorna um DataFrame vazio se não houver arquivo
            return pd.DataFrame()

        dados_raw = pd.read_csv(set_gdb('geof/') + arquivo_xyz)
        dados = self.renomear_geof(dados_raw)
        return self.selecionar_dados_geofisicos(dados, tipo, extend_size)

    # Método para adicionar dados geofisicos a folha
    def adicionar_geofisica(self, gama_xyz=None, mag_xyz=None, extend_size=0):
        '''
        Este método adiciona dados geofísicos à folha.

        Sintaxe:
        adicionar_geofisica(gama_xyz=None, mag_xyz=None, extend_size=0)

        Parâmetros:
        gama_xyz: nome do arquivo xyz de gama
        mag_xyz: nome do arquivo xyz de magnetometria
        extend_size: tamanho da extensão da bbox da folha

        '''
        gama_df = self.carregar_e_selecionar_geofisica(gama_xyz,
                                                       'gama_xyz', extend_size)
        mag_df = self.carregar_e_selecionar_geofisica(mag_xyz,
                                                      'mag_xyz', extend_size)

        return gama_df, mag_df

    # Método para remover folhas sem dados do dicionário de folhas
    def remover_quadriculas_sem_dados(self):
        '''
        Este método remove folhas sem dados do dicionário de folhas.

        Sintaxe:
        remover_quadriculas_sem_dados(folhas)

        Parâmetros:
        folhas: dicionário de folhas

        '''
        # Lógica para remover quadriculas sem dados
        for id in tqdm(list(self.folhas.keys())):
            columns = list(self.folhas[id].keys())
            # Caso a quadricula tenha apenas a geometria e o id ela é removida
            if len(self.folhas[id]) <= 2:
                self.folhas.pop(id)
            # Caso a quadricula possua menos de 5000 pontos ela é removida
            # REVISÃO
            elif len(self.folhas[id][columns[2]]) < 5000:
                self.folhas.pop(id)
        return self.folhas

    # Método para renomear colunas de dados geofísicos
    def renomear_geof(self, df):
        renomeacoes = {}
        if 'LAT_WGS' in df.columns:
            renomeacoes['LAT_WGS'] = 'LATITUDE'
            renomeacoes['LONG_WGS'] = 'LONGITUDE'
        if 'eTH' in df.columns:
            renomeacoes['eTH'] = 'eTh'
        df.rename(columns=renomeacoes, inplace=True)
        return df
