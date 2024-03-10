# Autor: Gabriel Góes Rocha de Lima
# Data: 01/02/2024
# source/core/ConstruirFolhas.py
# Última modificação: 09/03/2024
# ---------------------------------------------------------------------------
# Esta classe é responsável por criar geometrias de folhas de meta_cartas de
# acordo com a escala, salvar cada uma das meta_cartas como uma layer em um
# geoPackage ou um Postgres.
#
# Ela só será executada apenas uma vez para criar as folhas de meta_cartas e o
# geopackage ou o Postgres.

# ------------------------------ IMPORTS ------------------------------------
import math
from tqdm import tqdm
from shapely.geometry import mapping, Polygon
from utils.utils import set_db, float_range, meta_cartas, brasil, delimt

import fiona
from fiona.crs import CRS
# import psycopg2

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry

# ------------------------------ DATABASE ------------------------------------
Base = declarative_base()
url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/geodatabase'


# ------------------------------ CLASSES ------------------------------------
class CartografiaSistematica(Base):
    '''
    Esta classe é responsável por criar as folhas de meta_cartas de acordo com
    a escala.

    Exemplo:
        cs = CartografiaSistematica()
        cs.criar_folhas_de_meta_cartas('1kk')
        carta_1kk = cs.folhas
        cs.criar_folhas_de_meta_cartas('500k')
        carta_500k = cs.folhas
        cs.criar_folhas_de_meta_cartas('250k')
        folhas_250k = cs.folhas
        cs.criar_folhas_de_meta_cartas('100k')
        carta_100k = cs.folhas
        cs.criar_folhas_de_meta_cartas('50k')
        carta_50k = cs.folhas
        cs.criar_folhas_de_meta_cartas('25k')
        carta_25k = cs.folhas

        # lista de meta_cartas
        lista_meta_cartas = [carta_1kk, carta_500k, carta_250k,
                        carta_100k, carta_50k, carta_25k]

        # Salvar folhas de meta_cartas
        [cs.salvar_folhas_de_meta_cartas(carta) for carta in lista_cartas]

    '''
    __tablename__ = 'folhas_cartograficas'
    fid = Column(Integer, primary_key=True, autoincrement=True)
    wkb_geometry = Column(Geometry('POLYGON'))
    folha_id = Column(String, nullable=False)
    epsg = Column(String, nullable=False)
    escala = Column(String, nullable=False)

    # Construtor da classe CartografiaSistematica
    def __init__(self):
        self.folhas = {}
        self.carta = None

# -------------------------------- MÉTODOS ------------------------------------
    @staticmethod
    def gerar_id(left, right, top, bottom):
        '''
        Gera o id da folha de acordo com a escala (Carta).
        '''
        # Adquire o valor de carta do método criar_folhas
        e1kk = meta_cartas['1kk']['codigos']
        e500k = meta_cartas['500k']['codigos']
        e250k = meta_cartas['250k']['codigos']
        e100k = meta_cartas['100k']['codigos']
        e50k = meta_cartas['50k']['codigos']
        e25k = meta_cartas['25k']['codigos']
        if left > right:
            print('Oeste deve ser menor que leste')
        if top < bottom:
            print('Norte deve ser maior que Sul')
        else:
            folha_id = ''
            if top <= 0:
                folha_id += 'S'
                index = math.floor(-top / 4)
            else:
                folha_id += 'N'
                index = math.floor(bottom / 4)
            numero = math.ceil((180 + right) / 6)
            folha_id += e1kk[index] + str(numero)
            lat_gap = abs(top - bottom)
            # p500k-----------------------
            if lat_gap <= 2:
                LO = math.ceil(right / 3) % 2 == 0
                NS = math.ceil(top / 2) % 2 != 0
                folha_id += '_' + e500k[LO][NS]
            # p250k-----------------------
            if lat_gap <= 1:
                LO = math.ceil(right / 1.5) % 2 == 0
                NS = math.ceil(top) % 2 != 0
                folha_id += e250k[LO][NS]
            # p100k-----------------------
            if lat_gap <= 0.5:
                LO = (math.ceil(right / 0.5) % 3) - 1
                NS = math.ceil(top / 0.5) % 2 != 0
                folha_id += '_' + e100k[LO][NS]
            # p50k------------------------
            if lat_gap <= 0.25:
                LO = math.ceil(right / 0.25) % 2 == 0
                NS = math.ceil(top / 0.25) % 2 != 0
                folha_id += e50k[LO][NS]
            # p25k------------------------
            if lat_gap <= 0.125:
                LO = math.ceil(right / 0.125) % 2 == 0
                NS = math.ceil(top / 0.125) % 2 != 0
                folha_id += e25k[LO][NS]
            return folha_id

    def arredondar(self, numero, multiplo, arredondar_para_cima=False):
        if arredondar_para_cima:
            return math.ceil(numero / multiplo) * multiplo
        else:
            return math.floor(numero / multiplo) * multiplo

    @staticmethod
    def get_epsg(folha_id):
        if folha_id.startswith('S'):
            return '327' + folha_id[2:4]
        else:
            return '326' + folha_id[2:4]

    # Método para criar as folhas de meta_cartas
    def criar_folhas(self, carta):
        '''
        Cria as folhas de meta_cartas de acordo com a escala (Carta).
        '''
        self.carta = carta
        lat_incremen, lon_incremen = meta_cartas[carta]['incrementos']
        (lon_min_brasil, lat_min_brasil,
         lon_max_brasil, lat_max_brasil) = brasil.bounds

        # Arredonde os limites para os múltiplos mais próximos do incremento
        lat_min = self.arredondar(lat_min_brasil, lat_incremen)
        lon_min = self.arredondar(lon_min_brasil, lon_incremen)
        lat_max = self.arredondar(lat_max_brasil, lat_incremen,
                                  True)
        lon_max = self.arredondar(lon_max_brasil, lon_incremen,
                                  True)
        lat_ranges = [(i, i + lat_incremen) for i in float_range(lat_min,
                                                                 lat_max,
                                                                 lat_incremen)]
        lon_ranges = [(i, i + lon_incremen) for i in float_range(lon_min,
                                                                 lon_max,
                                                                 lon_incremen)]
        print(f' -> Criando folhas de carta {carta}')
        for lat_range in tqdm(lat_ranges):
            for lon_range in lon_ranges:
                polygon = Polygon([(lon_range[0], lat_range[0]),
                                   (lon_range[1], lat_range[0]),
                                   (lon_range[1], lat_range[1]),
                                   (lon_range[0], lat_range[1]),
                                   (lon_range[0], lat_range[0])])
                # Seleciona apenas poligonos que intersectam com o Brasil
                if polygon.intersects(brasil):
                    left, bottom, right, top = polygon.bounds
                    folha_id = self.gerar_id(left,
                                             right,
                                             top,
                                             bottom)
                    self.folhas[folha_id] = polygon
        print(delimt)

        return self.carta

    # Método para salvar as camadas em um geopackage com fiona
    def salvar_folhas_gpkg(self, folhas=None, file_name='fc.gpkg'):
        '''
        Salva as folhas de meta_cartas em um geopackage.
        '''
        print(' -> Salvando folhas de meta_cartas em geopackage\n')
        if self.folhas is None:
            print('Crie as folhas cartográficas primeiro')
            return
        if folhas is None:
            folhas = self.folhas
        carta = self.carta
        # Esquema para geopackage
        schema = {
            'geometry': 'Polygon',
            'properties': {'folha_id': 'str',
                           'epsg': 'str'}
        }
        # Define o CRS como WGS84
        crs = CRS.from_epsg(4326)
        # Nome da camada baseada na carta
        layer_name = f'fc_{carta}'
        # Cria o geopackage
        with fiona.open(set_db(file_name), 'w', driver='GPKG',
                        crs=crs, layer=layer_name, schema=schema) as layer:

            for folha_id, poligono in folhas.items():
                epsg_code = self.get_epsg(folha_id)
                # Adiciona o poligono e o id da folha no geopackage
                element = {
                    'geometry': mapping(poligono),
                    'properties': {'folha_id': folha_id,
                                   'epsg': epsg_code}
                }
                layer.write(element)

    # Método para salvar as camadas em um banco de dados
    def salvar_folhas_geodatabase(self, engine_url=url):
        '''
        Salva as folhas de meta_cartas em banco de dados.
        '''
        print(' -> Salvando cartas no banco de dados\n')
        if self.folhas is None:
            print('Crie as folhas cartográficas primeiro')
            return
        print(f' -> Salvando folhas de carta {self.carta} no banco de dados\n')

        engine = create_engine(engine_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Itera sobre as folhas e adiciona ao banco de dados
        for folha_id, poligono in self.folhas.items():
            epsg_code = self.get_epsg(folha_id)

            nova_folha = CartografiaSistematica()
            nova_folha.folha_id = folha_id
            nova_folha.epsg = epsg_code
            nova_folha.wkb_geometry = 'SRID={};{}'.format(epsg_code,
                                                          poligono.wkt)
            nova_folha.escala = self.carta

            session.add(nova_folha)
        # Salva as folhas no banco de dados
        session.commit()
        session.close()


# ----------------------- MAIN -----------------------------------------------
if __name__ == "__main__":
    print('')
    print(' Executando Script: ConstruirFolhas.py')
    print(delimt)
    cs = CartografiaSistematica
# Teste da classe DicionarioFolhas
# 1 : 1.000.000
    folhas_1kk = cs()
    folhas_1kk.criar_folhas('1kk')

# 1 : 500.000
    folhas_500k = cs()
    folhas_500k.criar_folhas('500k')

# 1 : 250.000
    folhas_250k = cs()
    folhas_250k.criar_folhas('250k')

# 1 : 100.000
    folhas_100k = cs()
    folhas_100k.criar_folhas('100k')

# 1 : 50.000
    folhas_50k = cs()
    folhas_50k.criar_folhas('50k')

# 1 : 25.000
    folhas_25k = cs()
    folhas_25k.criar_folhas('25k')

# Lista de meta_cartas
    lista_meta_cartas = [folhas_1kk, folhas_500k, folhas_250k,
                         folhas_100k, folhas_50k, folhas_25k]

# Salvar meta_cartas em um geopackage
#     [carta.salvar_folhas_gpkg() for carta in lista_meta_cartas]

# Salvar meta_cartas em um banco de dados
    [carta.salvar_folhas_geodatabase() for carta in lista_meta_cartas]
