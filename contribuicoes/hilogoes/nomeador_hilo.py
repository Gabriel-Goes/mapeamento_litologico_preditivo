import math

# Nomeador de Grids ------------------------------------------------------------------------------------------#
def nomeador_grid(left,right,top,bottom,escala=5):
    e1kk=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    e500k=[['V','Y'],['X','Z']]
    e250k=[['A','C'],['B','D']]
    e100k=[['I','IV'],['II','V'],['III','VI']]
    e50k=[['1','3'],['2','4']]
    e25k=[['NW','SW'],['NE','SE']]

    if left>right:
        print('Oeste deve ser menor que leste')
    if top<bottom:
        print('Norte deve ser maior que Sul')
    
    else:
        id_folha=''
        if top<=0:
            id_folha+='S'
            index=math.floor(-top/4)
        else:
            id_folha+='N'
            index=math.floor(bottom/4)
        
        numero=math.ceil((180+right)/6)
        id_folha+=e1kk[index]+str(numero)

        lat_gap=abs(top-bottom)
        #p500k-----------------------
        if (lat_gap<=2) & (escala>=1):
            LO=math.ceil(right/3)%2==0
            NS=math.ceil(top/2)%2!=0
            id_folha+='_'+e500k[LO][NS]
        #p250k-----------------------
        if (lat_gap<=1) & (escala>=2):
            LO=math.ceil(right/1.5)%2==0
            NS=math.ceil(top)%2!=0
            id_folha+=e250k[LO][NS]
        #p100k-----------------------
        if (lat_gap<=0.5) & (escala>=3):
            LO=(math.ceil(right/0.5)%3)-1
            NS=math.ceil(top/0.5)%2!=0
            id_folha+='_'+e100k[LO][NS]
        #p50k------------------------
        if (lat_gap<=0.25) & (escala>=4):
            LO=math.ceil(right/0.25)%2==0
            NS=math.ceil(top/0.25)%2!=0
            id_folha+='_'+e50k[LO][NS]
        #p25k------------------------
        if (lat_gap<=0.125) & (escala>=5):
            LO=math.ceil(right/0.125)%2==0
            NS=math.ceil(top/0.125)%2!=0
            id_folha+=e25k[LO][NS]
        return id_folha
