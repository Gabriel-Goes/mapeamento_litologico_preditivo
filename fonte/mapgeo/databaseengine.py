# Autor: Gabriel Góes Rocha de Lima
# Data: 11/03/2024
# ---------------------------------------------------------------------------
# source/core/DatabaseEngine.py
# Descrição: Este módulo é responsável por criar a engine do banco de dados
# e a sessão do banco de dados.
#
# ------------------------------- IMPORTS ------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry


# ------------------------------ PARAMETR ------------------------------------
url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/geodatabase'
Base = declarative_base()


# ------------------------------ CLASSES ------------------------------------
class DatabaseEngine:
    _instance = None

    def __new__(cls, url=url):
        if cls._instance is None:
            cls._instance = super(DatabaseEngine, cls).__new__(cls)
            cls._instance.engine = create_engine(url)
            cls._instance.Session = sessionmaker(bind=cls._instance.engine)
            Base.metadata.create_all(cls._instance.engine)
        return cls._instance

    @classmethod
    def get_engine(cls):
        return cls()._instance.engine

    @classmethod
    def get_session(cls):
        return cls()._instance.Session()


class Folha(Base):
    __tablename__ = 'fc'
    codigo = Column(String, primary_key=True)
    epsg = Column(String, nullable=False)
    escala = Column(String, nullable=False)
    geometry = Column(Geometry('POLYGON'), name="wkb_geometry")  # Nome correto da coluna de geometria

    def __repr__(self):
        return f"<Folha(codigo={self.codigo}, epsg={self.epsg}, escala={self.escala})>"
