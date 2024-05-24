# Autor: Gabriel Góes Rocha de Lima
# Data: 11/03/2024
# ---------------------------------------------------------------------------
# source/core/GamaTables.py
# Descrição: Este módulo é responsável por criar tabela de gama no banco de
# dados.
#
# ------------------------------- IMPORTS ------------------------------------
from sqlalchemy import Column, Integer, Float
from geoalchemy2 import Geometry

from DatabaseEngine import Base


# ------------------------------ CLASSES ------------------------------------
class Gama(Base):
    '''
    Classe responsável por criar a tabela de gama.
    '''
    __tablename__ = 'gama'
    id = Column(Integer, primary_key=True)
    x = Column(Float)
    y = Column(Float)
    longitude = Column(Float)
    latitude = Column(Float)
    thc = Column(Float)
    uc = Column(Float)
    kc = Column(Float)
    ctc = Column(Float)
    mdt = Column(Float)
    geom = Column(Geometry('POINT'))
