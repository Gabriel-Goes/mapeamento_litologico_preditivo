# Autor: Gabriel Góes Rocha de Lima
# Data: 2024/02/07
# /source/core/LerFolhas.py
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar os ids, e geometry de cada folha.
# ------------------------------ IMPORTS ------------------------------------
import geopandas as gpd
from utils import setDB


# ------------------------------ CLASSES ------------------------------------
class AbrirFolhas:
    # Construtor da classe
    def __init__(self, gpkg='fc.gpkg'):
        '''
        Construtor da classe DicionarioFolhas.
        Recebe como parâmetro:
            file: str - arquivo geopackage
        Retorna:
            file: str - caminho do arquivo geopackage
        '''
        try:
            self.file = setDB(gpkg)
            print(f'--> Arquivo {self.file} carregado com sucesso!')
        except Exception as e:
            print(f'--> Erro ao carregar o arquivo! {e}')
            print('--> Aqui deve ser seus geopackage.gpkg!')

    # Método para importar a carta da escala escolhida
    def seleciona_escala(self, escala):
        '''
        Método responsável por importar as folhas de carta na escala escolhida.
            Recebe como parâmetro:
                carta: str - escalas disponíveis: 25k, 50k, 100k,
                                                  250k, 500k e 1kk
            Retorna:
                carta: gdf - geodataframe com a carta escolhida
        '''
        try:
            # Lê o arquivo geopackage
            self.cartas = gpd.read_file(self.file, layer='fc_' + escala)

            return self.cartas
        except Exception as e:
            print(f' --> Erro ao importar a carta! {e}')
            print(' --> Escalas disponíveis: 25k, 50k, 100k, 250k, 500k e 1kk')

    # Define área de estudo
    def define_area_de_estudo(self, id_folha_area_de_estudo):
        '''
        Método responsável por definir a área de estudo.
        Recebe como parâmetros:
            cartas: gdf - geodataframe com as cartas
            id_folha_area_de_estudo: str - id da folha da área de estudo
        Retorna:
            folha_ade: gdf - geodataframe com a folha da área de estudo
        '''
        folha_ade = self.cartas[
            self.cartas['id_folha'] == id_folha_area_de_estudo]

        return folha_ade

    # Criar bounding box para a folha escolhida
    @staticmethod
    def cria_bbox(folha_ade):
        # Cria a bounding box
        minx, miny = folha_ade.bounds.minx, folha_ade.bounds.miny
        maxx, maxy = folha_ade.bounds.maxx, folha_ade.bounds.maxy
        bbox = (minx + 0.125, miny + 0.125, maxx - 0.125, maxy - 0.125)
        return bbox

    # Ler todas as folhas da carta escolhida contidas na id_folha_estudo
    def segmenta_area_de_estudo(self, folha_ade, escala):
        '''
        Método responsável por ler todas as folhas da carta escolhida que estão
        contidas na folha com 'id_folha' = id_folha_estudo.
        Recebe como parâmetros:
            folhas_area_de_estudo: gdf - geodataframe com a folha da area
            de estudo
            carta: str - carta escolhida
        Retorna:
            folhas_estudo: gdf - geodataframe com as folhas da carta escolhida
        '''
        # Cria a bounding box
        bbox = self.cria_bbox(folha_ade)
        try:
            # Lê o arquivo geopackage
            folhas_area_de_estudo = gpd.read_file(self.file,
                                                  layer=f'fc_{escala}',
                                                  driver='GPKG',
                                                  bbox=bbox)
            return folhas_area_de_estudo

        except KeyError:
            print(' --> Erro ao segmentar a área de estudo!')

    # Filtrar folhas de da área de estudo
    @staticmethod
    def filtrar_folhas_estudo(folhas_area_de_estudo, id_folhas):
        '''
        Método responsável por filtrar as folhas da área de estudo.
        Recebe como parâmetros:
            folhas_estudo: gdf - geodataframe com as folhas da carta escolhida
                   folhas: str - id da folha de estudo
        '''
        # Filtra macro_gdf pr id_folha
        return folhas_area_de_estudo[folhas_area_de_estudo[
            'id_folha'].str.contains(id_folhas)]


# ------------------------------ EXECUÇÃO ------------------------------------
if __name__ == '__main__':
    # Teste da classe AbrirFolhas
    # Cria um objeto da classe AbrirFolhas
    folhas = AbrirFolhas()
    # Importa a carta da escala 1:1.000.000
    carta_1kk = folhas.seleciona_escala('1kk')
    # Define a folha da área de estudo
    SF23 = folhas.define_area_de_estudo('SF23')
    # Segmenta a área de estudo na escala desejada
    folhas_25k_SF23 = folhas.segmenta_area_de_estudo(SF23, '25k')
    # Filtra as folhas da área de estudo
    folhas_25k_SF23_YA = folhas.filtrar_folhas_estudo(folhas_25k_SF23,
                                                      'SF23_YA')
    print(f' -> número de folhas: {folhas_25k_SF23_YA.size}')
    print(folhas_25k_SF23_YA.head())
