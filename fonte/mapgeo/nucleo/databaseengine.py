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

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# ------------------------------ PARAMETR ------------------------------------
url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/geodatabase'
Base = declarative_base()


# ------------------------------ CLASSES ------------------------------------
class DatabaseEngine:
    _instance = None

    def __new__(cls, url=url):
        logging.info(f"Creating new instance of DatabaseEngine with url: {url}")
        if cls._instance is None:
            cls._instance = super(DatabaseEngine, cls).__new__(cls)
            cls._instance.engine = create_engine(url)
            cls._instance.Session = sessionmaker(bind=cls._instance.engine)
            Base.metadata.create_all(cls._instance.engine)
            logging.info(f"DatabaseEngine instance created with url: {url}")
        return cls._instance

    @classmethod
    def get_engine(cls):
        return cls()._instance.engine

    @classmethod
    def get_session(cls):
        return cls()._instance.Session()


class Folha(Base):
    logging.info("Creating Folha class")
    __tablename__ = 'folhas_cartograficas'
    codigo = Column(String, primary_key=True)
    epsg = Column(String, nullable=False)
    escala = Column(String, nullable=False)
    geometry = Column(Geometry('POLYGON'), name="wkb_geometry")  # Nome correto da coluna de geometria
    logging.info("Folha class created")

    def __repr__(self):
        logging.info(f"Creating representation of Folha with codigo={self.codigo}, epsg={self.epsg}, escala={self.escala}")
        logging.info(f"Geometry: {self.geometry}")

        return f"<Folha(codigo={self.codigo}, epsg={self.epsg}, escala={self.escala})>"
