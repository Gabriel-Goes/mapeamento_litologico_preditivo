import geopandas as gpd


gdb = '/home/ggrl/geodatabase/'


# Importador de Litologias por escala
def litologia(escala):
    lito =  gpd.read_file(gdb+'geodatabase.gpkg',
                        driver= 'GPKG',
                        layer= escala)
    return(lito)



# Selecionador de Mapas a partir do nome
def mapa(escala,nome):
    folha = escala[escala.MAPA == 'Carta geológica da folha '+nome]
    return(folha)







