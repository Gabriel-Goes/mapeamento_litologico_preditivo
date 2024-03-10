# Autor: Gabriel Góes Rocha de Lima
# Data: 2024/02/07
# /source/core/LerFolhas.py
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar os ids, e geometry de cada folha.
# ------------------------------ IMPORTS ------------------------------------
import fiona
from shapely import geometry

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry

from utils import set_db, gdb_url


# ------------------------------ PARÂMETROS ---------------------------------
Base = declarative_base()


# ------------------------------ CLASSES ------------------------------------
class FolhasCartograficas(Base):
    '''
    Classe responsável por criar a tabela de folhas cartográficas.
    '''
    __tablename__ = 'folhas_cartograficas'
    fid = Column(Integer, primary_key=True)
    folha_id = Column(String)
    wkb_geometry = Column(Geometry('POLYGON'))
    epsg = Column(String)
    escala = Column(String)


class AbrirFolhas:
    # Construtor da classe
    def __init__(self, gpkg='fc.gpkg', gdb_url=gdb_url):
        '''
        Construtor da classe DicionarioFolhas.
        Recebe como parâmetro:
            file: str - arquivo geopackage
        Retorna:
            file: str - caminho do arquivo geopackage
        '''
        try:
            print('-> Inicializando AbrirFolhas')
            self.file = set_db(gpkg)
            self.gdb_url = gdb_url
            self.engine = create_engine(self.gdb_url)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            self.cartas = {}

        except Exception as e:
            print('--> AbrirFolhas Falhou!')
            print(f' !ERROR": {e}')
            print('--> Aqui deve ser seus geopackage.gpkg!')

    # Método para importar a carta da escala escolhida de um PostGIS
    def seleciona_escala_postgres(self, escala: str):
        '''
        Método responsável por importar as folhas de carta na escala escolhida
        de um banco de dados PostGIS.
            Recebe como parâmetro:
                carta: str - escalas disponíveis: 25k, 50k, 100k,
                                                  250k, 500k e 1kk
            Retorna:
                carta: gdf - geodataframe com a carta escolhida
        '''
        try:
            # Consulta str(escala) em banco de dados
            consulta = self.session.query(FolhasCartograficas).filter(
                FolhasCartograficas.escala == escala).all()
            # consulta = self.session.query(FolhasCartograficas).filter(
            #     FolhasCartograficas.folha_id.like(f'%{escala}%')).all()
            # Transforma a consulta em uma geometria
            print(consulta[1].wkb_geometry)
            print(consulta[1].epsg)
            print(consulta[1].escala)
            print(consulta[1].folha_id)
            carta = geometry.MultiPolygon([{
                'geometry': folha.wkb_geometry,
                'folha_id': folha.folha_id,
                'epsg': folha.epsg,
                'escala': folha.escala
            } for folha in consulta])
            print(f'-> Carta {carta} importada com sucesso!')
            return carta

        except Exception as e:
            print(f' --> Erro ao importar a carta! {e}')
            print(' --> Escalas disponíveis: 25k, 50k, 100k, 250k, 500k e 1kk')
            return consulta

    # Método para importar a carta da escala escolhida de um geopackage
    def seleciona_escala_gpkg(self, escala: str) -> fiona.Collection:
        '''
        Método responsável por importar as folhas de carta na escala escolhida.
            Recebe como parâmetro:
                carta: str - escalas disponíveis: 25k, 50k, 100k,
                                                  250k, 500k e 1kk
            Retorna:
                carta: gdf - geodataframe com a carta escolhida
        '''
        try:
            self.cartas.clear()
            # Lê o arquivo geopackage com fiona
            with fiona.open(self.file, layer=f'fc_{escala}') as collection:
                for feature in collection:
                    geom = feature['geometry']
                    folha_id = feature['properties']['folha_id']
                    epsg = feature['properties']['epsg']
                    self.cartas[folha_id] = {
                        'geometry': geom,
                        'folha_id': folha_id,
                        'epsg': epsg
                    }
            print(f' --> Carta {escala} importada com sucesso!')
            return self.cartas

        except Exception as e:
            print('')
            print(' --> AbrirFolhas.seleciona_escala_gpkg falhou!')
            print(f' ! ERROR: {e}')
            print('')
            print(f' --> escala: {escala}')

    # Define área de estudo
    def define_area_de_estudo(self,
                              id_folha_area_de_estudo: str):
        '''
        Método responsável por definir a área de estudo.
        Recebe como parâmetros:
            cartas: gdf - geodataframe com as cartas
            id_folha_area_de_estudo: str - id da folha da área de estudo
        Retorna:
            folha_ade: gdf - geodataframe com a folha da área de estudo
        '''
        folha_ade = self.cartas[
            self.cartas['folha_id'] == id_folha_area_de_estudo]
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
    def segmenta_area_de_estudo(self, area_de_estudo, escala):
        '''
        Método responsável por ler todas as folhas da carta escolhida que estão
        contidas na folha com 'folha_id' = id_folha_estudo.
        Recebe como parâmetros:
            folhas_area_de_estudo: gdf - geodataframe com a folha da area
            de estudo
            carta: str - carta escolhida
        Retorna:
            folhas_estudo: gdf - geodataframe com as folhas da carta escolhida
        '''
        # spatial join em cada folha_da_area_de_estudo

        # Cria a bounding box
        print(f' --> Escala: {escala}')
        print(f' --> Area de estudo: {area_de_estudo}')
        bbox = self.cria_bbox(area_de_estudo)
        print(f' bbox: {bbox}')
        try:
            # Lê o arquivo geopackage com fiona filtrando por bbox
            pass

        except KeyError:
            print(' --> Erro ao segmentar a área de estudo!')

    # Filtrar folhas de da área de estudo
    @staticmethod
    def filtrar_folhas_estudo(folhas_area_de_estudo, folha_ids):
        '''
        Método responsável por filtrar as folhas da área de estudo.
        Recebe como parâmetros:
            folhas_estudo: gdf - geodataframe com as folhas da carta escolhida
                   folhas: str - id da folha de estudo
        '''
        # Filtra macro_gdf por folha_id
        return folhas_area_de_estudo[folhas_area_de_estudo[
            'folha_id'].str.contains(folha_ids)]


# ------------------------------ EXECUÇÃO ------------------------------------
if __name__ == '__main__':
    # Teste da classe AbrirFolhas
    # Cria um objeto da classe AbrirFolhas
    folhas = AbrirFolhas()
    # Importa a carta da escala 1:1.000.000
    carta_1kk = folhas.seleciona_escala_gpkg('1kk')
    # Define a folha da área de estudo
    SF23 = folhas.define_area_de_estudo('SF23')
    print(f' --> Folha da área de estudo: {SF23}')
    # Segmenta a área de estudo na escala desejada
    folhas_25k_SF23 = folhas.segmenta_area_de_estudo(SF23, '25k')
    # Filtra as folhas da área de estudo
    folhas_25k_SF23_YA = folhas.filtrar_folhas_estudo(folhas_25k_SF23,
                                                      'SF23_YA')
    print(f' -> número de folhas: {folhas_25k_SF23_YA.size}')
    print(folhas_25k_SF23_YA.head())
