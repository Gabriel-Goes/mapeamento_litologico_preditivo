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
def interpolar(mag=None,gama=None,
               dic_cartas=None,dic_raw_meta=None):
    print('# Inicio dos processos de interpolação pelo método cúbico')
    for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):

        lista_atributo_geof = dic_raw_meta['Lista_at_geof']
        data = dic_cartas['raw_data'][index]              

        # GERANDO TUPLA DE COORDENADAS
        if data.empty:
            None
            
        elif len(data) < 1000:
            None
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Retirando dados brutos em dic_cartas['raw_data']")
            print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de 500 metros")

            data['geometry'] = [geometry.Point(x, y) for x, y in zip(data['X'], data['Y'])]
            crs = "+proj=utm +zone=23 +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs"

            gdf_geof = gpd.GeoDataFrame(data, geometry='geometry', crs=crs)

            area = dic_cartas['region_proj'][index]

            # creating a grid with cells
            xu, yu = td.regular(shape = (636, 444),
                                area  = area)

            if mag:
                ALTURA = np.array(gdf_geof.ALTURA)
                MAGIGRF = np.array(gdf_geof.MAGIGRF)
                MDT = np.array(gdf_geof.MDT)

                x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                altura_ = td.interp_at(x2, y2, ALTURA, xu, yu, algorithm = 'cubic', extrapolate = True)
                mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                magigrf_ = td.interp_at(x2, y2, MAGIGRF, xu, yu, algorithm = 'cubic', extrapolate = True)

                # intialise data of lists. 
                data_interpolado = {'X':xu, 'Y':yu, 'MDT': mdt_,
                        'KPERC': altura_, 'eU':magigrf_} 
                
                # Create DataFrame 
                interpolado_cubico = pd.DataFrame(data_interpolado)
                
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

                dic_cartas['cubic'] = {}                
                y={index:interpolado_cubico}
                dic_cartas['cubic'].update(y)

            print('__________________________________________')
        print(" ")
    print("Dicionário de cartas disponível")
    return dic_cartas, dic_raw_meta