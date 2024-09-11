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
from shapely.geometry import mapping
from shapely. geometry import Polygon

import fiona
from fiona.crs import CRS

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Index

from geoalchemy2 import Geometry

from utils import get_epsg
from utils import set_db
from utils import float_range
from utils import meta_cartas
from utils import brasil
from utils import delimt

from DatabaseEngine import DatabaseEngine
from DatabaseEngine import Base

# ------------------------------ PARAMETROS ---------------------------------


# ------------------------------ CLASSES ------------------------------------
class CartografiaSistematica(Base):
    '''
    Esta classe é responsável por criar as folhas de meta_cartas de acordo com
    a escala.

    '''
    __tablename__ = 'folhas_cartograficas'
    fid = Column(Integer, primary_key=True, autoincrement=True)
    wkb_geometry = Column(Geometry('POLYGON'))
    codigo = Column(String, nullable=False)
    epsg = Column(String, nullable=False)
    escala = Column(String, nullable=False)

    __table_args__ = (
        Index('ix_folhas_cartograficas_geom',
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
                    codigo = self.gerar_id(left,
                                           right,
                                           top,
                                           bottom)
                    self.folhas[codigo] = polygon
        print(delimt)

        return self.folhas

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
            'properties': {'codigo': 'str',
                           'epsg': 'str'}
        }
        # Define o CRS como WGS84
        crs = CRS.from_epsg(4326)
        # Nome da camada baseada na carta
        layer_name = f'fc_{carta}'
        # Cria o geopackage
        with fiona.open(set_db(file_name), 'w', driver='GPKG',
                        crs=crs, layer=layer_name, schema=schema) as layer:

            for codigo, poligono in folhas.items():
                epsg_code = get_epsg(codigo)
                # Adiciona o poligono e o id da folha no geopackage
                element = {
                    'geometry': mapping(poligono),
                    'properties': {'codigo': codigo,
                                   'epsg': epsg_code}
                }
                layer.write(element)

    # Método para salvar as camadas em um banco de dados
    def salvar_folhas_geodatabase(self):
        '''
        Salva as folhas de meta_cartas em banco de dados utilizando a
        engine e session fornecidas pela classe singleton DatabaseEngine.
        '''
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
                print(nova_folha.__tablename__)
                session.add(nova_folha)
            # Salva as folhas no banco de dados
            session.commit()
        except Exception as e:
            print(f' Erro ao salvar folhas no banco de dados: - {e}')
            session.rollback()
        session.close()


def test():
    '''
    Função para criar folhas de meta_cartas de acordo com a escala (Carta).
    '''
    print(delimt)
    print(' -> Criando folhas de meta_cartas')
    print(delimt)
    cs = CartografiaSistematica()
    for carta in meta_cartas:
        print(carta)
        cs.criar_folhas(carta=carta)
        cs.salvar_folhas_geodatabase()
        # cs.salvar_folhas_gpkg()


# ----------------------- MAIN -----------------------------------------------
if __name__ == "__main__":
    print('')
    print(' Executando Script: ConstruirFolhas.py')
    print(delimt)
    test()
