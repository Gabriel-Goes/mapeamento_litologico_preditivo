# OUTPUT DO SCRPIT/GET_REGION SERA O INPUT DESTE SCRIPT
from scripts.get_region import get_region
from sources import descricao as d
from sources.importar import geometrias

from contribuicoes.victsnet_emails import source_code_verde as td

import verde as vd
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely import geometry
from tqdm import tqdm

gdb = '/home/ggrl/geodatabase/'


# # --------------------- DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES -------------- 
def interpolar(escala, id, geof,
               psize=None, spacing=None, degree=None, n_splits=None,
               camada=None, mapa=None,
               crs__ = 'geografica', describe=False,
               save=None,
               tdm=None,
               mag=None,gama=None,
               selecionar=False, dic_cartas=False, dic_raw_meta =False):


    # RECORTANDO REGIOES E DESCRENDO DADOS
    if selecionar:
        dic_cartas,dic_raw_meta = get_region(escala,id,geof,camada,mapa)       
                                                    #           Dicionario de Metadatas['Lista_id',            #1 DICIONARIO COM METADADOS
                                                    #                                   'Lista_at_geof', 
                                                    #                                   'Lista_at_geog',
                                                    #                                   'Lista_at_proj']      

    else:
        for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):

            lista_atributo_geof = dic_raw_meta['Lista_at_geof']
            data = dic_cartas['raw_data'][index]              

            # REMOVENDO VALORES NEGATIVOS DOS DADOS AEROGAMAESPECTOMETRICOS
            for atr in dic_raw_meta['Lista_at_geof']:                   # LEMBRAR DE MELHOR ISSO
                if atr == 'KPERC':
                    data.loc[data.KPERC < 0, 'KPERC'] = 0
                    data.loc[data.eU < 0, 'eU'] = 0
                    data.loc[data.eTH < 0, 'eTH'] = 0
                    data.loc[data.CTCOR < 0, 'CTCOR'] = 0


            # ----------------------------------------------------------------------------------------------------------------------
            # CALCULANDO RAZOES DE BANDAS PARA OS DADOS
            '''
            a,b,c,d,e = descricao(data)
            # Calculo de normalizaçao dos dados para seguir com a razao de bandas min = 10% da media dos dados
            data_razoes = data   # criando uma nova variavel para ser alterada

            data_razoes.loc[data_razoes.eU < (e['eU']['mean']) / 10, 'eU'] = (e['eU']['mean']) / 10
            data_razoes.loc[data_razoes.KPERC < (e['KPERC']['mean']) / 10, 'KPERC'] = (e['KPERC']['mean']) / 10
            data_razoes.loc[data_razoes.eth   < (e['eth']['mean'])   / 10, 'eTH'] = (e['eTH']['mean']) / 10
            # Razao de bandas
            data['U_TH'] = data_razoes.eU / data_razoes.eth
            data['U_K']  = data_razoes.eU  / data_razoes.KPERC
            data['TH_K']  = data_razoes.eth / data_razoes.KPERC
            '''
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
                dic_cartas['raw_data'].update(x) 
                print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de {spacing} metros")
                
                # ADICIONANDO ATRIBUTOS GEOFÍSICOS AO DICIONÁRIO splines
                splines={}
                for atributo in lista_atributo_geof:
                    x = {atributo:''}
                    splines.update(x)
                #print(f" Construindo dic_cartas['splines'] vazio com os atributos geofísicos")
                    
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
                if degree:
                # Iterando entre os canais de interpolação
                    print("")
                    print(f"# --- Inicio da interpolação com verde Splines # ")
                    for i in tqdm(lista_atributo_geof):
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
                        chain.fit(coordinates,data[i])

                        # Griding the predicted data.
                        #print(f"Predicting values of '{i}' to a regular grid of {psize} m")
                        grid = chain.grid(spacing=psize, data_names=[i],pixel_register=True)
                        splines[i] = vd.distance_mask(coordinates, maxdist=1000, grid= grid)
                        
                        # ATUALIZAÇÃO DE DICIONÁRIO DE splines
                        x = {index:splines}
                        dic_cartas['splines'].update(x)
                        #print(f" Dicionário de dados splines da folha {index} atualizados")

                        # Processo de validação cruzada da biblioteca verde
                        if n_splits:
                            cv     = vd.BlockKFold(spacing=spacing,
                                        n_splits=n_splits,
                                        shuffle=True)
                            #print(f"Parâmetros de validação cruzada: {cv}")
                            scores[i] = vd.cross_val_score(chain,
                                                    coordinates,
                                                    data[i],
                                                    cv=cv,
                                                    delayed=True)

                            import dask
                            mean_score[i] = dask.delayed(np.mean)(scores[i])
                            print("Delayed mean:", mean_score)
                    
                            print(f"Computing mean scores of  '{i}' variable...")
                            mean_score[i] = mean_score[i].compute()
                            #print(f"Mean score: {mean_score}")
                            

                        # ATUALIZAÇÃO DE DICIONÁRIO DE SCORES
                        y = {index:scores}
                        dic_cartas['scores'].update(y)

                        x = {index:mean_score}
                        dic_cartas['mean_score'].update(x)
                        print(f"# Folha {index} atualizada ao dicionário{list(dic_cartas.keys())}")

                        
                        # SALVANDO DADOS INTERPOLADOS NO FORMATO .TIF
                        if save:
                            local='grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif'
                            print('salvando grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif')
                            #grids[i].to_netcdf(gdb+'/grids/geof_3022_'+str(psize)+'m_'+i+'_'+row.id_folha+'.nc')
                            tif_ = splines[i].rename(easting = 'x',northing='y')
                            tif_.rio.to_raster(gdb+local)

                if tdm == 'cubico':
                    for i in tqdm(lista_atributo_geof):
                        
                        geof = data

                        geof['geometry'] = [geometry.Point(x, y) for x, y in zip(geof['X'], geof['Y'])]
                        crs = "+proj=utm +zone=23 +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs"

                        gdf_geof = gpd.GeoDataFrame(geof, geometry='geometry', crs=crs)

                        area = dic_cartas['region_proj'][index]

                        # creating a grid with cells
                        xu, yu = td.regular(shape = (636, 444),
                                            area  = area)

                        #lista_atributos_geof = ['MDT', 'KPERC', 'eU', 'eth', 'CTCOR', 'THKRAZAO', 'UKRAZAO', 'UTHRAZAO']
                        #lista_atributos_geof = ['ALTURA', 'MDT', 'MAGIGRF']
                        if mag:
                            ALTURA = np.array(gdf_geof.ALTURA)
                            MAGIGRF = np.array(gdf_geof.MAGIGRF)
                            MDT = np.array(gdf_geof.MDT)

                            x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                            altura_ = td.interp_at(x2, y2, ALTURA, xu, yu, algorithm = 'cubic', extrapolate = True)
                            mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                            magigrf_ = td.interp_at(x2, y2, MAGIGRF, xu, yu, algorithm = 'cubic', extrapolate = True)
    
                            # intialise data of lists. 
                            data = {'X':xu, 'Y':yu, 'MDT': mdt_,
                                    'KPERC': altura_, 'eU':magigrf_} 
                            
                            # Create DataFrame 
                            interpolado_cubico = pd.DataFrame(data)
                            
                            # Print the output. 
                            y={index:interpolado_cubico}
                            dic_cartas['cubic'].update(y)  

                        if gama:
                            CTCOR = np.array(gdf_geof.CTCOR)

                            MDT = np.array(gdf_geof.MDT)

                            eTH = np.array(gdf_geof.eTH)

                            eU = np.array(gdf_geof.eU)

                            KPERC = np.array(gdf_geof.KPERC)

                            THKRAZAO = np.array(gdf_geof.THKRAZAO)

                            UKRAZAO = np.array(gdf_geof.UKRAZAO)

                            UTHRAZAO = np.array(gdf_geof.UTHRAZAO)


                            x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)


                            eTH_ = td.interp_at(x2, y2, eTH, xu, yu, algorithm = 'cubic', extrapolate = True)
                            eu_ = td.interp_at(x2, y2, eU, xu, yu, algorithm = 'cubic', extrapolate = True)
                            kperc_ = td.interp_at(x2, y2, KPERC, xu, yu, algorithm = 'cubic', extrapolate = True)
                            ctcor_ = td.interp_at(x2, y2, CTCOR, xu, yu, algorithm = 'cubic', extrapolate = True)
                            mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                            uthrazao_ = td.interp_at(x2, y2, UTHRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                            ukrazao_ = td.interp_at(x2, y2, UKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                            thkrazao_ = td.interp_at(x2, y2, THKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                            # intialise data of lists. 
                            data = {'X':xu, 'Y':yu, 'MDT': mdt_,  'CTCOR': ctcor_,
                                    'KPERC': kperc_, 'eU':eu_, 'eTH': eTH_,
                                    'UTHRAZAO':uthrazao_,'UKRAZAO':ukrazao_,'THKRAZAO':thkrazao_} 
                            
                            # Create DataFrame 
                            interpolado_cubico = pd.DataFrame(data)
                            
                            # Print the output. 
                            y={index:interpolado_cubico}
                            dic_cartas['cubic'].update(y)                
            
                # RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
                if describe:
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
                    
                    # GRID POR SPLINES
                    if degree:
                        for i in tqdm(lista_atributo_geof):
                            df = splines[i].to_dataframe()
                            lista_interpolado.append(df[i])

                        geof_splines = pd.concat(lista_interpolado,axis=1, join='inner')
                        geof_splines.reset_index(inplace=True)
                        geof_splines['geometry'] =\
                        [geometry.Point(x,y) for x, y in zip(geof_splines['easting'], geof_splines['northing'])]
                            

                        # AJUSTANDO CRS
                        #print("Ajustando crs")
                        if crs__=='proj':
                            gdf = gpd.GeoDataFrame(geof_splines,crs=32723)
                            gdf = gdf.set_crs(32723, allow_override=True)
                            gdf = gdf.to_crs("EPSG:32723")
                            print(f" geof: {gdf.crs}")
                        else:
                            gdf = gpd.GeoDataFrame(geof_splines,crs=32723)
                            gdf = gdf.set_crs(32723, allow_override=True)
                            gdf = gdf.to_crs("EPSG:4326")
                            print(f" geof: {gdf.crs}")

                        # CALCULO DE GEOMETRIA MAIS PROXIMA
                        print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_splines)} centróides de pixel")
                        lito_splines = geof_splines
                        lito_splines['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])
                        print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
                        print(f"  {list(lito_splines['closest_unid'].unique())}")

                        # Adicionando lito_geof ao dicionario
                        print('')
                        print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
                        x = {index:lito_splines}
                        dic_cartas['lito_splines'].update(x)
                        print(dic_cartas['lito_splines'][index].keys())


                    # GRID POR CUBICO
                    if tdm:
                        for i in tqdm(lista_atributo_geof):
                            df = interpolado_cubico[i].to_dataframe()
                            lista_interpolado.append(df[i])

                        geof_cubic = pd.concat(lista_interpolado,axis=1, join='inner')
                        geof_cubic.reset_index(inplace=True)

                        # AJUSTANDO CRS
                        #print("Ajustando crs")
                        if crs__=='proj':
                            gdf = gpd.GeoDataFrame(geof_splines,crs=32723)
                            gdf = gdf.set_crs(32723, allow_override=True)
                            gdf = gdf.to_crs("EPSG:32723")
                            print(f" geof: {gdf.crs}")
                        else:
                            gdf = gpd.GeoDataFrame(geof_splines,crs=32723)
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


                    print('__________________________________________')
                print(" ")
        print("Dicionário de cartas disponível")
        return dic_cartas, dic_raw_meta