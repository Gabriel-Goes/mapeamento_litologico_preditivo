







# # --------------------- DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES -------------- 
def interpolar(escala,id,geof,standard_verde=None,psize=None,spacing=None,degree=None,n_splits=None,
               camada=None,nome=None,crs__='geografica',describe=False):
    # DEFININDO PADRÃO DE INTERPOLAÇÃO VERDE
    if standard_verde:
        save=None
        degree=1
        spacing=499
        psize= 100
    else:
        save=None
        degree=degree
        spacing=spacing
        psize=psize

    # RECORTANDO REGIOES E DESCRENDO DADOS
    data_list = f.get_region(escala,id,geof)    
                                                 #           Dicionario de Metadatas['Lista_id',            #1 DICIONARIO COM METADADOS
                                                 #                                   'Lista_at_geof', 
                                                 #                                   'Lista_at_geog',
                                                 #                                   'Lista_at_proj']      
    data_list[1]['Lista_at_geof'].append('U_TH')
    data_list[1]['Lista_at_geof'].append('U_K')
    data_list[1]['Lista_at_geof'].append('TH_K')

    for index, row in tqdm(data_list[2].iterrows()):

        lista_atributo_geof = data_list[1]['Lista_at_geof']
        dic_cartas = data_list[0]
        data = data_list[0]['raw_data'][index]              

        # REMOVENDO VALORES NEGATIVOS DOS DADOS AEROGAMAESPECTOMETRICOS
        data.loc[data.KPERC < 0, 'KPERC'] = 0
        data.loc[data.eU < 0, 'eU'] = 0
        data.loc[data.eTH < 0, 'eTH'] = 0

        # ----------------------------------------------------------------------------------------------------------------------
        # CALCULANDO RAZOES DE BANDAS PARA OS DADOS
        a,b,c,d,e = f.descricao(data)
        
        # Calculo de normalizaçao dos dados para seguir com a razao de bandas min = 10% da media dos dados
        data_razoes = data   # criando uma nova variavel para ser alterada

        data_razoes.loc[data_razoes.eU < (e['eU']['mean']) / 10, 'eU'] = (e['eU']['mean']) / 10
        data_razoes.loc[data_razoes.KPERC < (e['KPERC']['mean']) / 10, 'KPERC'] = (e['KPERC']['mean']) / 10
        data_razoes.loc[data_razoes.eTH   < (e['eTH']['mean'])   / 10, 'eTH'] = (e['eTH']['mean']) / 10
        # Razao de bandas
        data['U_TH'] = data_razoes.eU / data_razoes.eTH
        data['U_K']  = data_razoes.eU  / data_razoes.KPERC
        data['TH_K']  = data_razoes.eTH / data_razoes.KPERC
        # ----------------------------------------------------------------------------------------------------------------------

        # GERANDO TUPLA DE COORDENADAS
        if data.empty:
            None
            
        elif len(data) < 1000:
            None
            #print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Atualizando dados brutos em dic_cartas['raw_data']")
            x = {index:data}
            data_list[0]['raw_data'].update(x) 
            print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de {spacing} metros")
            
            # ADICIONANDO ATRIBUTOS GEOFÍSICOS AO DICIONÁRIO INTERPOLADO
            interpolado={}
            for atributo in lista_atributo_geof:
                x = {atributo:''}
                interpolado.update(x)
            #print(f" Construindo dic_cartas['interpolado'] vazio com os atributos geofísicos")
                
            # ADICIONANDO ATRIBUTOS AO DICIONÁRIO SCORES
            scores={}
            for atributo in lista_atributo_geof:
                y = {atributo:''}
                scores.update(y)

            mean_score={}
            for atributo in lista_atributo_geof:
                x = {atributo:''}
                mean_score.update(x)    

            #print(f" Construindo dicionário vazio de score do cross validation")

            # Iterando entre os canais de interpolação
            print("")
            print(f"# --- Inicio da interpolação com verde Splines # ")
            for i in lista_atributo_geof:
                # Definindo encadeamento de processsos para interpolação
                chain = vd.Chain([
                                ('trend', vd.Trend(degree=degree)),
                                ('reduce', vd.BlockReduce(np.mean, spacing=spacing)),
                                ('spline', vd.Spline())
                            ])
                
                #print(f"Encadeamento: {chain}") 
                coordinates = (data.X.values, data.Y.values)
                
                # ESCOLHER MELHOR TRAIN TEST SPLIT


                print(f"Fitting Model of  '{i}' variable...")
                chain.fit(coordinates, data[i])

                # Griding the predicted data.
                #print(f"Predicting values of '{i}' to a regular grid of {psize} m")
                grid = chain.grid(spacing=psize, data_names=[i],pixel_register=True)
                interpolado[i] = vd.distance_mask(coordinates, maxdist=1000, grid= grid)
                
                # ATUALIZAÇÃO DE DICIONÁRIO DE INTERPOLADOS
                x = {index:interpolado}
                dic_cartas['interpolado'].update(x)
                #print(f" Dicionário de dados interpolados da folha {index} atualizados")

                # Processo de validação cruzada da biblioteca verde
                if n_splits:
                    cv     = vd.BlockKFold(spacing=spacing,
                                n_splits=n_splits,
                                shuffle=True)
                    print(f"Parâmetros de validação cruzada: {cv}")

                    scores[i] = vd.cross_val_score(chain,
                                            coordinates,
                                            data[i],
                                            cv=cv,
                                            delayed=False)

                    scores[i] = vd.cross_val_score(chain,
                                            coordinates,
                                            data[i],
                                            cv=cv,
                                            delayed=True)

                    import dask
                    mean_score[i] = dask.delayed(np.mean)(scores[i])
                    #print("Delayed mean:", mean_score)

                    mean_score[i] = mean_score[i].compute()
                    #print(f"Mean score: {mean_score}")


                # ATUALIZAÇÃO DE DICIONÁRIO DE SCORES
                #print(f" Atualizando dicionário com scores")
                y = {index:scores}
                dic_cartas['scores'].update(y)

                x = {index:mean_score}
                dic_cartas['mean_score'].update(x)
                print(f"# Folha {index} atualizada ao dicionário")

                
                # SALVANDO DADOS INTERPOLADOS NO FORMATO .TIF
                if save:
                    local='grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif'
                    print('salvando grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif')
                    #grids[i].to_netcdf(gdb+'/grids/geof_3022_'+str(psize)+'m_'+i+'_'+row.id_folha+'.nc')
                    tif_ = interpolado[i].rename(easting = 'x',northing='y')
                    tif_.rio.to_raster(gdb+local)
        
            # RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
            if describe:
                print("")
                print(f"# --- Inicio da análise geoestatística")
                lista_interpolado = list()

                for i in lista_atributo_geof:
                    df = interpolado[i].to_dataframe()
                    lista_interpolado.append(df[i])

                geof_grids = pd.concat(lista_interpolado,axis=1, join='inner')
                geof_grids.reset_index(inplace=True)
                geof_grids['geometry'] =\
                     [geometry.Point(x,y) for x, y in zip(geof_grids['easting'], geof_grids['northing'])]

                print('Ajustando crs')
                if crs__=='proj':
                    gdf = gpd.GeoDataFrame(geof_grids,crs=32723)
                    gdf = gdf.set_crs(32723, allow_override=True)
                    gdf = gdf.to_crs("EPSG:32723")
                    print(f" geof: {gdf.crs}")
                else:
                    gdf = gpd.GeoDataFrame(geof_grids,crs=32723)
                    gdf = gdf.set_crs(32723, allow_override=True)
                    gdf = gdf.to_crs("EPSG:4326")
                    print(f" geof: {gdf.crs}")

                # IMPORTANDO VETORES LITOLÓGICOS
                litologia = f.importar(camada,nome)
                litologia.reset_index(inplace=True)
                if crs__=='proj':
                    litologia = litologia.set_crs(32723, allow_override=True)
                    litologia = litologia.to_crs("EPSG:32723")
                    print(f" lito: {litologia.crs}")
                else:
                    litologia = litologia.set_crs(32723, allow_override=True)
                    litologia = litologia.to_crs("EPSG:4326")
                    litologia=litologia.cx[row.region[0]:row.region[1],row.region[2]:row.region[3]]
                    litologia.reset_index(inplace=True)
                    print(f" lito: {litologia.crs}")


                print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_grids)} centróides de pixel")
                #print(f"# Listagem de unidade geológicas do mapa litologia['MAPA'].unique():")
                #print(f" {list(litologia['litologia'].unique())}")
                lito_geof = geof_grids
                lito_geof['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['litologia'].iloc[litologia.distance(x).idxmin()])
                print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
                print(f"  {list(lito_geof['closest_unid'].unique())}")

                # Adicionando lito_geof ao dicionario
                print('')
                print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
                x = {index:lito_geof}
                dic_cartas['lito_geof'].update(x)
                print(dic_cartas['lito_geof'][index].keys())

                print('__________________________________________')
            print(" ")
    print("Dicionário de cartas disponível")
    return dic_cartas, data_list
