import pandas as pd


def set_gdb(filepath=None):
    gdb = '/home/ggrl/geodatabase/' + filepath

    return gdb


def import_xyz(filename, rowskiped):
    data_cols = 'KB DATA BARO UB THB COSMICO CTB UUP ALTURA KPERC eU eTH CTEXP\
    UTHRAZAO X Y UKRAZAO MDT THKRAZAO LIVE_TIME CTCOR KCOR THCOR UCOR HORA\
    GPSALT LATITUDE FIDUCIAL TEMP LONGITUDE'.split(" ")

    geof = pd.read_csv(set_gdb('xyz/' + filename),
                       names=data_cols,
                       delim_whitespace=True,
                       skiprows=rowskiped,
                       usecols=["X", "Y", "LATITUDE", "LONGITUDE",
                                "KPERC", "eU", "eTH", "CTCOR",
                                "THKRAZAO", "UTHRAZAO", "UKRAZAO", "MDT"])

    return geof


# Dado Aerogeofísico
geof = import_xyz('1105_GamaLine.XYZ', 10)
geof.dropna(inplace=True)

print(geof.head(10))
print(geof.info())


def list_columns(geof):
    print('Listando atributos dos dados geofisicos')
    atributos_geof = list(geof.columns)             # DataFrame.columns
    lista_atributo_geof = []
    lista_atributo_geog = []
    lista_atributo_proj = []

    for atributo in atributos_geof:
        if atributo == 'LATITUDE':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LONGITUDE':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LONG':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LAT':
            lista_atributo_geog.append(atributo)
        elif atributo == 'X':
            lista_atributo_proj.append(atributo)
        elif atributo == 'Y':
            lista_atributo_proj.append(atributo)
        elif atributo == 'UTME':
            lista_atributo_proj.append(atributo)
        elif atributo == 'UTMN':
            lista_atributo_proj.append(atributo)
        elif atributo == 'X_WGS':
            lista_atributo_proj.append(atributo)
        elif atributo == 'Y_WGS':
            lista_atributo_proj.append(atributo)
        else:
            lista_atributo_geof.append(atributo)

    # codigo =str(geof)

    print("# --- # Listagem de dados do aerolevantamento:  ")
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")
    return lista_atributo_geof, lista_atributo_geog, lista_atributo_proj


meta_listas = list_columns(geof)
dicionario = {'': ''}
