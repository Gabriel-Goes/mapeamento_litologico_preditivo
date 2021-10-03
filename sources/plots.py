from sources import importar
import matplotlib.pyplot as plt

# FUNÇOES DE PLOTAGEM COM GEOPANDAS
def plot_brazil(gdf,atributo=None):
    world = importar.gpd.read_file(importar.gpd.datasets.get_path('naturalearth_lowres'))
    brazil = world[world.name == 'Brazil']
    if atributo:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(atributo,ax=ax)
    else:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(ax=ax)

def plot_base(gdf,atributo=None,escala=None,nome=None):
    litologia = importar.geologico(escala,nome)

    if atributo:
        ax = litologia.plot('SIGLA')
        gdf.plot(atributo,color='black',ax=ax)
    else:
        ax = litologia.plot('SIGLA')
        gdf.plot(ax=ax,color='black')

def labels(gdf):
    gdf['coords'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
    gdf['coords'] = [coords[0] for coords in gdf['coords']]

    for index, row in gdf.iterrows():
        plt.annotate(text=row['id_folha'], xy=row['coords'],horizontalalignment='center')

# ----------------------------------------------------------------------------------------------------------------------