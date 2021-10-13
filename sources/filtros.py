
#### Filtro de LITOTIPOS


def filtro(gdf,mineral):
    '''
    Recebe uma camada vetorial e uma 'str', navega pela coluna LITOTIPOS selecionando geometrias que contem a 'str'

    Caso nenhuma geometria seja selecionada, retornara a lista de valores unicos presenta na coluna LITOTIPOS da camada vetorial


    '''
    filtrado = gdf[gdf['LITOTIPOS'].str.contains(mineral)]
    if filtrado.empty:
        print(f"{list(gdf['LITOTIPOS'].unique())}")
    else:
        return filtrado


