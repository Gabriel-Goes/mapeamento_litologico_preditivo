<<<<<<< HEAD:interface_preditor.py
from src import (import_mc, Build_mc, Upload_geof)
from shapely.ops import transform
import pyproj
from tkinter import (Label, Tk, Frame, Button)
from tkinter.ttk import Combobox
from tk import *
import matplotlib.pyplot as plt
=======
from src import set_gdb, import_mc, Build_mc, Upload_geof, Upload_litologia
from shapely import geometry
from shapely.ops import transform
import pyproj
from tkinter import *
from tkinter import ttk
import geopandas as gpd
from tqdm import tqdm
>>>>>>> dev:interface/interface_preditor.py
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
import warnings
warnings.filterwarnings("ignore")
<<<<<<< HEAD:interface_preditor.py


# -----------------------------Main Frame----------------------------
janela = Tk()
=======
import matplotlib.pyplot as plt
#-----------------------------Main Frame----------------------------
janela=Tk()
>>>>>>> dev:interface/interface_preditor.py
janela.title('Preditor de Litologias')
titulo = Label(text='Preditor de Litologias', font=('Arial', 12))
titulo.pack()

<<<<<<< HEAD:interface_preditor.py

#  -----------------------------Funçõees------------------------------ 
=======
#-----------------------------Funçõees-------------------------------
>>>>>>> dev:interface/interface_preditor.py
def list_id():
    mc = import_mc(cmb_escala.get())
    lista_id = list(mc['id_folha'])
    return lista_id


def scale_select(event):
    cmb_folhas['values'] = list_id()


def build_dic():
    print(' - CONSTRUINDO DICIONÁRIO DE CARTAS')
    escala = cmb_escala.get()
    ID = cmb_folhas.get()
<<<<<<< HEAD:interface_preditor.py
    quadricula = Build_mc(escala, [ID], verbose=True)
    folha = quadricula[ID]['folha']
    fig = Figure(figsize=(5, 5), dpi=100)
=======
    quadricula = Build_mc(escala,[ID],verbose=True)
    folha=quadricula[ID]['area']
    fig = Figure(figsize=(5,5),dpi=100)
>>>>>>> dev:interface/interface_preditor.py
    wgs84 = pyproj.CRS('EPSG:4326')
    EPSG = folha['EPSG']
    utm = pyproj.CRS('EPSG:'+EPSG)
    carta_wgs84 = folha['geometry']
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    carta_utm = transform(project, carta_wgs84)
    plot1 = fig.add_subplot(111)
    plot1.plot(*carta_utm.exterior.xy)
    canvas = FigureCanvasTkAgg(fig, janela)
    canvas.draw()
    canvas.get_tk_widget().pack()
    toolbar = NavigationToolbar2Tk(canvas, janela)
    toolbar.update()
    return quadricula, ID, escala


def upload_dic():
<<<<<<< HEAD:interface_preditor.py
    quadricula, ID, escala = build_dic()
    Upload_geof(quadricula, gama_xyz='gama_line_1105', mag_xyz='mag_line_1105')
    df = quadricula[ID]['gama']
    coords = [df.X, df.Y]
    scatter = FigureCanvasTkAgg(fig, janela)
=======
    quadricula,ID,escala=build_dic()
    Upload_mc(quadricula,gama_xyz='gama_line_1105',mag_xyz='mag_line_1105',camada='socorro_250k')
    df = quadricula[ID]['gama']
    coords = [df.X,df.Y]

    scatter = FigureCanvasTkAgg(fig,janela)
>>>>>>> dev:interface/interface_preditor.py
    scatter.get_tk_widget().pack()
    plt.scatter(coords[0], coords[1], s=1.5, c=df.MDT, cmap='terrain')
    plt.axis('scaled')
    return quadricula


# -------------------------Seletor de Área--------------------------
frame_seletor = Frame(janela)
lbl_seletor = Label(frame_seletor, text='Seletor de Área')
lbl_seletor.grid(row=0, column=0, padx=5, pady=5)
frame_seletor['relief'] = 'sunken'
frame_seletor['borderwidth'] = 2
<<<<<<< HEAD:interface_preditor.py
=======
# --- Seletor de Escalas
escalas=['25k','50k','100k','250k','1kk']
lbl_escala = ttk.Label(frame_seletor,text='Escalas Disponíveis',font=('Arial',9))
lbl_escala['relief'] = 'raised'
lbl_escala.grid(row=1,column=0,padx=5)
cmb_escala = ttk.Combobox(frame_seletor,values=escalas)
cmb_escala.grid(row=1,column=1)
cmb_escala.bind('<<ComboboxSelected>>',scale_select)
# --- Seletor de Folhas
lbl_folhas = ttk.Label(frame_seletor,text='Folhas Disponíveis',font=('Arial',9))
lbl_folhas['relief'] = 'raised'
lbl_folhas.grid(row=2,column=0)
cmb_folhas = ttk.Combobox(frame_seletor)
cmb_folhas.grid(row=2,column=1)
frame_seletor.pack()
# -------------------------Construtor de Quadriculas--------------------------
frame_quadricula = ttk.Frame(janela)
lbl_quadricula = ttk.Label(frame_quadricula,text='Malha Cartográfica')
lbl_quadricula.grid(row=0,column=0,padx=5,pady=5)
frame_quadricula['relief']='sunken'
frame_quadricula['borderwidth']=2
# --- Botão Construtor de Quadriculas
btn_build=ttk.Button(frame_quadricula,command=build_dic)
btn_build.grid(row=0,column=1)
build_lbl=ttk.Label(frame_quadricula,text='Construir')
build_lbl.grid(row=0,column=1)
# --- Botão Plot function
btn_upload=ttk.Button(frame_quadricula,command=upload_dic)
btn_upload.grid(row=1,column=1)
lbl_upload=ttk.Label(frame_quadricula,text='Upload')
lbl_upload.grid(row=1,column=1)
# --- Visualizador de qudriculas
>>>>>>> dev:interface/interface_preditor.py

# --- Seletor de Escalas
escalas = ['25k', '50k', '100k', '250k', '1kk']
lbl_escala = Label(frame_seletor, text='Escalas Disponíveis',
                   font=('Arial', 9))
lbl_escala['relief'] = 'raised'
lbl_escala.grid(row=1, column=0, padx=5)
cmb_escala = Combobox(frame_seletor, values=escalas)
cmb_escala.grid(row=1, column=1)
cmb_escala.bind('<<ComboboxSelected>>', scale_select)

# --- Seletor de Folhas
lbl_folhas = Label(frame_seletor,
                   text='Folhas Disponíveis',
                   font=('Arial', 9))
lbl_folhas['relief'] = 'raised'
lbl_folhas.grid(row=2, column=0)
cmb_folhas = Combobox(frame_seletor)
cmb_folhas.grid(row=2, column=1)
frame_seletor.pack()


# -------------------------Construtor de Quadriculas--------------------------
frame_quadricula = Frame(janela)
lbl_quadricula = Label(frame_quadricula, text='Malha Cartográfica')
lbl_quadricula.grid(row=0, column=0, padx=5, pady=5)
frame_quadricula['relief'] = 'sunken'
frame_quadricula['borderwidth'] = 2

#          ### Botão Construtor de Quadriculas ###
btn_build = Button(frame_quadricula, command=build_dic)
btn_build.grid(row=0, column=1)
build_lbl = Label(frame_quadricula, text='Construir')
build_lbl.grid(row=0, column=1)

#          ###       Botão Plot function      ###
btn_upload = Button(frame_quadricula, command=upload_dic)
btn_upload.grid(row=1, column=1)
lbl_upload = Label(frame_quadricula, text='Upload')
lbl_upload.grid(row=1, column=1)

#          ###    Visualizador de qudriculas ###
frame_quadricula.pack()

# --- Set Start Parameters
cmb_folhas.set('SF23_YA_III')
cmb_escala.set('100k')


# -------------------------Executor--------------------------------------------
janela.mainloop()
