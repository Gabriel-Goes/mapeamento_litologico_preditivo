from tqdm import tqdm
import pandas as pd
import geopandas as gpd

# RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
def describe(dic_cartas,dic_raw_data,crs__,tdm,):
    print("")
    print(f"# --- Inicio da análise geoestatística")
    lista_interpolado = list()

    # IMPORTANDO VETORES LITOLÓGICOS ------------
    litologia = dic_cartas['litologia'][index]
    litologia.reset_index(inplace=True)
    
    if crs__=='proj':
        litologia.to_crs(32723,inplace=True)
        print(f" lito: {litologia.crs}")
    else:
        litologia.to_crs(4326,inplace=True)
        print(f" lito: {litologia.crs}")
    # -------------------------------------------
    
    # GRID POR CUBICO
    if tdm:
        for i in tqdm(dic_raw_data['lista_atributo_geof']):
            df = dic_cartas['interpolado_cubico'][i].to_dataframe()
            lista_interpolado.append(df[i])

        geof_cubic = pd.concat(lista_interpolado,axis=1, join='inner')
        geof_cubic.reset_index(inplace=True)

        # AJUSTANDO CRS
        #print("Ajustando crs")
        if crs__=='proj':
            gdf = gpd.GeoDataFrame(geof_cubic,crs=32723)
            gdf = gdf.set_crs(32723, allow_override=True)
            gdf = gdf.to_crs("EPSG:32723")
            print(f" geof: {gdf.crs}")
        else:
            gdf = gpd.GeoDataFrame(geof_cubic,crs=32723)
            gdf = gdf.set_crs(32723, allow_override=True)
            gdf = gdf.to_crs("EPSG:4326")
            print(f" geof: {gdf.crs}")


        # CALCULO DE GEOMETRIA MAIS PROXIMA
        print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_cubic)} centróides de pixel")
        lito_cubic = dic_cartas['cubic'][index]
        lito_cubic['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])
        print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
        print(f"  {list(lito_cubic['closest_unid'].unique())}")

        # Adicionando lito_geof ao dicionario
        print('')
        print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
        x = {index:lito_cubic}
        dic_cartas['lito_cubic'].update(x)
        print(dic_cartas['lito_cubic'][index].keys())