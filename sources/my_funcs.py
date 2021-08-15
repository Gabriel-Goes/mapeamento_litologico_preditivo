import geopandas as gpd
import math

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

'''
# Selecionador de ocorrências
def ocrr(substancia):
    ocorrencias= gpd.read_file(gdb+'geodatabase.gpkg',
                              driver= 'GPKG',
                              layer= 'ocorr_min')
    
    subs= ocorrencias
'''





# Nomeador de Grids
p1kk=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
p500k=[['V','Y'],['X','Z']]
p250k=[['A','C'],['B','D']]
p100k=[['I','IV'],['II','V'],['III','VI']]
p50k=[['1','3'],['2','4']]

def nomeador_grid(left,right,top,bottom,escala=4):
    if left>right:
        print('Oeste deve ser menor que leste')
    if top<bottom:
        print('Norte deve ser maior que Sul')
    
    else:
        folha=''
        if top<0:
            folha+='S'
            north=False
            index=math.floor(-top/4)
        else:
            folha+='N'
            north=True
            index=math.floor(bottom/4)
        
        numero=math.ceil((180+right)/6)
        folha+=p1kk[index]+str(numero)

        
        lat_gap=abs(top-bottom)
        #p500k-----------------------
        if (lat_gap<=2) & (escala>=1):
            LO=math.ceil(right/3)%2==0
            NS=math.ceil(top/2)%2!=north
            folha+='_'+p500k[LO][NS]
        #p250k-----------------------
        if (lat_gap<=1) & (escala>=2):
            LO=math.ceil(right/1.5)%2==0
            NS=math.ceil(top)%2!=north
            folha+='_'+p250k[LO][NS]
        #p100k-----------------------
        if (lat_gap<=0.5) & (escala>=3):
            LO=(math.ceil(right/0.5)%3)-1
            NS=math.ceil(top/0.5)%2!=north
            folha+='_'+p100k[LO][NS]
        #p50k-----------------------
        if (lat_gap<=0.25) & (escala>=4):
            LO=math.ceil(right/0.25)%2==0
            NS=math.ceil(top/0.25)%2!=north
            folha+='_'+p50k[LO][NS]
        return folha



'''
# Selecionador de Região
    # Selecionar SF23 Folha Rio de Janeiro Escala 1:1.000.000
    # Selecionar Intersecção do aerolevantamento 1039



def get_region(region,escala)

    region = [-47.00, -46.75,
            -22.75, -22.50]

    geof_SF23_Y_A_V_4 = geof_1039[vd.inside((geof_1039.LONG, geof_1039.LAT), region = region)]

'''