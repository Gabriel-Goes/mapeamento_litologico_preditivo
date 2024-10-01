# Autor: Gabriel Góes Rocha de Lima
# Data: 01/02/2024
# Modificado: 24/03/2024
# fonte/nucleo/constroifolhas.py
# Última modificação: 09/03/2024
# Última modificação: 22/08/2024
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
from shapely. geometry import Polygon
import geopandas as gpd
import os

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Index

from geoalchemy2 import Geometry

from databaseengine import DatabaseEngine
from databaseengine import Base

# ------------------------------ PARAMETROS ---------------------------------
delimt = '------------------------------------------------------\n'


def set_db(path=''):
    return '/home/database/' + path


def list_files(path):
    return os.listdir(path)


def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step


def get_epsg(folha_id):
    if folha_id.startswith('S'):
        return '327' + folha_id[2:4]
    else:
        return '326' + folha_id[2:4]


# define geometria do Brasil
ibge = set_db('shapefiles/IBGE/')
regioes = gpd.read_file(ibge + 'ANMS2010_06_grandesregioes.shp')
brasil = regioes.unary_union

meta_cartas = {
    '1kk': {'escala': '1:1.000.000',
            'incrementos': (4, 6),
            'codigos': ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                        'H', 'I', 'J', 'K', 'L', 'M', 'N',
                        'O', 'P', 'Q', 'R', 'S', 'T']},
    '500k': {'escala': '1:500.000',
             'incrementos': (2, 3),
             'codigos': [['V', 'Y'], ['X', 'Z']]},
    '250k': {'escala': '1:250.000',
             'incrementos': (1, 1.5),
             'codigos': [['A', 'C'], ['B', 'D']]},
    '100k': {'escala': '1:100.000',
             'incrementos': (0.5, 0.5),
             'codigos': [['I', 'IV'], ['II', 'V'], ['III', 'VI']]},
    '50k': {'escala': '1:50.000',
            'incrementos': (0.25, 0.25),
            'codigos': [['1', '3'], ['2', '4']]},
    '25k': {'escala': '1:25.000',
            'incrementos': (0.125, 0.125),
            'codigos': [['NW', 'SW'], ['NE', 'SE']]}
}

reverse_meta_cartas = {meta_cartas[k]['escala']: k for k in meta_cartas}


# ------------------------------ CLASSES ------------------------------------
class CartografiaSistematica(Base):
    __tablename__ = 'folha_cartografica'
    fid = Column(Integer, primary_key=True, autoincrement=True)
    wkb_geometry = Column(Geometry('POLYGON'))
    codigo = Column(String, nullable=False)
    epsg = Column(String, nullable=False)
    escala = Column(String, nullable=False)
    __table_args__ = (
        Index('ix_folha_cartografica_geom',
              'wkb_geometry',
              postgresql_using='gist'),
    )

    # Construtor da classe CartografiaSistematica
    def __init__(self):
        self.folhas = {}
        self.carta = None

# -------------------------------- MÉTODOS ------------------------------------
    @staticmethod
    def gerar_id(left, right, top, bottom):
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
            codigo = ''
            if top <= 0:
                codigo += 'S'
                index = math.floor(-top / 4)
            else:
                codigo += 'N'
                index = math.floor(bottom / 4)
            numero = math.ceil((180 + right) / 6)
            codigo += e1kk[index] + str(numero)
            lat_gap = abs(top - bottom)
            # p500k-----------------------
            if lat_gap <= 2:
                LO = math.ceil(right / 3) % 2 == 0
                NS = math.ceil(top / 2) % 2 != 0
                codigo += '_' + e500k[LO][NS]
            # p250k-----------------------
            if lat_gap <= 1:
                LO = math.ceil(right / 1.5) % 2 == 0
                NS = math.ceil(top) % 2 != 0
                codigo += e250k[LO][NS]
            # p100k-----------------------
            if lat_gap <= 0.5:
                LO = (math.ceil(right / 0.5) % 3) - 1
                NS = math.ceil(top / 0.5) % 2 != 0
                codigo += '_' + e100k[LO][NS]
            # p50k------------------------
            if lat_gap <= 0.25:
                LO = math.ceil(right / 0.25) % 2 == 0
                NS = math.ceil(top / 0.25) % 2 != 0
                codigo += e50k[LO][NS]
            # p25k------------------------
            if lat_gap <= 0.125:
                LO = math.ceil(right / 0.125) % 2 == 0
                NS = math.ceil(top / 0.125) % 2 != 0
                codigo += e25k[LO][NS]
            return codigo

    def arredondar(self, numero, multiplo, arredondar_para_cima=False):
        if arredondar_para_cima:
            return math.ceil(numero / multiplo) * multiplo
        else:
            return math.floor(numero / multiplo) * multiplo

    # Método para criar as folhas de meta_cartas
    def criar_folhas(self, carta):
        self.folhas = {}
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
                if polygon.intersects(brasil):
                    left, bottom, right, top = polygon.bounds
                    codigo = self.gerar_id(left,
                                           right,
                                           top,
                                           bottom)
                    self.folhas[codigo] = polygon
        print(delimt)

        return self.folhas

    # Método para salvar as camadas em um banco de dados
    def salvar_folhas_geodatabase(self):
        print(' -> Salvando cartas no banco de dados\n')
        if self.folhas is None:
            print('Crie as folhas cartográficas primeiro')
            return
        print(f' -> Salvando folhas de carta {self.carta} no banco de dados\n')
        session = DatabaseEngine.get_session()
        try:
            # Itera sobre as folhas e adiciona ao banco de dados
            for codigo, poligono in self.folhas.items():
                nova_folha = CartografiaSistematica()
                nova_folha.codigo = codigo
                epsg_code = get_epsg(codigo)
                nova_folha.epsg = epsg_code
                nova_folha.wkb_geometry = 'SRID={};{}'.format(4326,
                                                              poligono.wkt)
                nova_folha.escala = self.carta
                session.add(nova_folha)
            # Salva as folhas no banco de dados
            session.commit()
        except Exception as e:
            print(f' Erro ao salvar folhas no banco de dados: - {e}')
            session.rollback()
        session.close()


def test():
    print(delimt)
    print(' -> Criando folhas de meta_cartas')
    print(delimt)
    cs = CartografiaSistematica()
    for carta in meta_cartas:
        print(carta)
        cs.criar_folhas(carta=carta)
        cs.salvar_folhas_geodatabase()


# ----------------------- MAIN -----------------------------------------------
if __name__ == "__main__":
    print('')
    print(' Executando Script: ConstruirFolhas.py')
    print(delimt)
    test()
