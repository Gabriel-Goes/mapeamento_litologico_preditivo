from src import *

class Malha_cartografica:
    def __init__(self, escala, ID):
        self.escala = escala
        self.ID = ID

    mc = import_mc(self.escala,self.ID)
    mc.set_index('id_folha',inplace=True)
    quadricula = {}
    wgs84 = pyproj.CRS('EPSG:4326')
    ids = list(quadricula.keys())

    for index, row in tqdm(mc.iterrows()):
        carta_wgs84 = row['geometry']
        utm = pyproj.CRS.('EPSG:' + row['EPSG'])
        project = pyproj.transform(wgs84,utm,always_xy=True).transform
        carta_utm = transform(project,carta_wgs84)








