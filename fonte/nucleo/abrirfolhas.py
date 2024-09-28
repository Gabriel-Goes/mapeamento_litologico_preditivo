# Autor: Gabriel Góes Rocha de Lima
# Data: 2024/02/07
# /fonte/nucleo/abrirfolhas.py
# Modificado: 2024/08/22
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar os ids, e geometry de cada folha.
# ------------------------------ IMPORTS ------------------------------------
from collections import UserDict
import fiona
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from nucleo.utils import set_db, gdb_url, delimt
from nucleo.databaseengine import DatabaseEngine
from typing import Dict


# ------------------------------ PARÂMETROS ---------------------------------
Base = declarative_base()


# ------------------------------ CLASSES ------------------------------------
class FolhasCartograficas(Base):
    __tablename__ = 'folhas_cartograficas'
    fid = Column(Integer, primary_key=True)
    codigo = Column(String)
    wkb_geometry = Column(Geometry('POLYGON'))
    epsg = Column(String)
    escala = Column(String)


class AttribDict(UserDict):
    """
    Dicionário que permite o acesso aos itens como atributos, evitando loops recursivos.
    """

    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise AttributeError(f"'AttribDict' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        if key == 'data':  # Evitar loop recursivo
            super().__setattr__(key, value)
        else:
            self.data[key] = value


class AbrirFolhas:
    def __init__(self, gpkg='fc.gpkg', gdb_url=gdb_url):
        '''
        Construtor da classe AbrirFolhas.
        Inicializa a conexão com o banco de dados e prepara o dicionário de folhas.
        '''
        try:
            print('-> Inicializando AbrirFolhas')
            self.file = set_db(gpkg)
            self.gdb_url = gdb_url
            self.engine = DatabaseEngine.get_engine()
            self.session = DatabaseEngine.get_session()
            self.dic_folhas = AttribDict()  # Utilizando AttribDict para folhas

        except Exception as e:
            print('--> AbrirFolhas Falhou!')
            print(f' !ERROR: {e}')

    def seleciona_escala_postgres(self, escala: str) -> AttribDict:
        '''
        Método responsável por importar as folhas de carta na escala escolhida
        de um banco de dados PostGIS.
        Retorna um AttribDict {'folha_id': {'geometry': geom, 'epsg': epsg, 'escala': escala}}.
        '''
        self.dic_folhas.clear()
        try:
            consulta = self.session.query(FolhasCartograficas).filter(
                FolhasCartograficas.escala == escala
            ).all()
            if not consulta:
                print(f' --> Nenhuma folha encontrada para a escala: {escala}')
                return self.dic_folhas

            for folha in consulta:
                self.dic_folhas[folha.codigo] = AttribDict({
                    'geometry': folha.wkb_geometry,
                    'epsg': folha.epsg,
                    'escala': folha.escala
                })

            print(f' --> {len(self.dic_folhas)} folhas_{escala} importadas')
            print(f'  {delimt}')
            return self.dic_folhas

        except Exception as e:
            print(' --> AbrirFolhas.seleciona_escala_postgres falhou!')
            print(f' !ERROR: {e}')
            print(f' --> escala: {escala}')

    def define_area_de_estudo(self, id_folha_area_de_estudo: str):
        '''
        Define a folha da área de estudo a partir do ID.
        '''
        return self.dic_folhas[id_folha_area_de_estudo]

    @staticmethod
    def cria_bbox(folha_ade):
        '''
        Cria uma bounding box (caixa delimitadora) para a folha de estudo.
        '''
        minx, miny = folha_ade.bounds.minx, folha_ade.bounds.miny
        maxx, maxy = folha_ade.bounds.maxx, folha_ade.bounds.maxy
        bbox = (minx + 0.125, miny + 0.125, maxx - 0.125, maxy - 0.125)
        return bbox

    def segmenta_area_de_estudo(self, area_de_estudo, escala):
        '''
        Segmenta a área de estudo com base na escala definida.
        '''
        print(f' --> Escala: {escala}')
        print(f' --> Area de estudo: {area_de_estudo}')
        bbox = self.cria_bbox(area_de_estudo)
        print(f' bbox: {bbox}')
        # Implementação para segmentar área de estudo, por exemplo, com fiona.

    @staticmethod
    def filtrar_folhas_estudo(folhas_area_de_estudo, codigos):
        '''
        Filtra folhas da área de estudo com base nos códigos fornecidos.
        '''
        return folhas_area_de_estudo[folhas_area_de_estudo['codigo'].str.contains(codigos)]


# ------------------------------ EXECUÇÃO ------------------------------------
if __name__ == '__main__':
    # Teste da classe AbrirFolhas
    folhas = AbrirFolhas()
    carta_1kk = folhas.seleciona_escala_postgres('1kk')
    SF23 = folhas.define_area_de_estudo('SF23')
    print(f' --> Folha da área de estudo: {SF23}')
    folhas_25k_SF23 = folhas.segmenta_area_de_estudo(SF23, '25k')
    folhas_25k_SF23_YA = folhas.filtrar_folhas_estudo(folhas_25k_SF23, 'SF23_YA')
    print(f' -> número de folhas: {folhas_25k_SF23_YA.size}')
    print(folhas_25k_SF23_YA.head())
