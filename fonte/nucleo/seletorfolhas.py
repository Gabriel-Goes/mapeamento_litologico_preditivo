# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# ./fonte/nucleo/seletorfolhas.py
# Modificado: 2024-08-22
# Descrição: Classe para implementar métodos de seleção de folhas.

# -----------------------------------------------------------------------------
from nucleo.utils import reverse_meta_cartas, delimt
from nucleo.plotfolhas import PlotFolhas
from typing import Dict
import shapely
# USE LOGGING
import logging

# ------------------------------ LOGGING ------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
f_handler = logging.FileHandler('./fonte/nucleo/seletorfolhas.log')
f_handler.setLevel(logging.DEBUG)
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)
logger.addHandler(c_handler)
logger.addHandler(f_handler)

# -----------------------------------------------------------------------------


# ------------------------------ CLASSES ------------------------------------
class SeletorFolhas:
    '''
    Classe para implementar métodos de seleção de folhas.
    Será instanciado por FrameSeletor e utilizado para atualizar valores
    de escala e atualizar folha de estudo e gerar dicionário de folhas.
    '''

    # ---------------------------- Construtor ---------------------------------
    def __init__(self,
                 combobox_cartas, combobox_folha,
                 admin_folhas):
        print('-> Iniciando SeletorFolhas')
        try:
            self.combobox_folha = combobox_folha
            self.combobox_cartas = combobox_cartas
            self.admin_folhas = admin_folhas
            self.folhas_estudo = {}
        except Exception as e:
            print(' --> SeletorFolhas falhou!')
            print(f' !ERROR!: {e}')
            print(' --> Parâmetros:')
            print(f' --> combobox_cartas: {combobox_cartas}')
            print(f' --> combobox_folha: {combobox_folha}')
            print(f' --> admin_folhas: {admin_folhas}')
            print(delimt)

    # ---------------------------- Métodos ------------------------------------
    def get_combobox_cartas(self):
        print(f' --> Escala escolhida: {self.combobox_cartas.get()}')
        self.escala = self.combobox_cartas.get()

    def evento_combobox_cartas(self, event):
        self.get_combobox_cartas()
        # self.selecionar_carta_gpkg(self.escala)
        self.selecionar_carta_postgres(self.escala)

    def atualizar_combobox_folha(self):
        # Atualiza valores de Combobox Folhas
        if self.cartas is not None:
            codigos = list(self.cartas.keys())
        else:
            print("ERRO: 'SELF.CARTAS' É NONE")
        self.id_folhas_original = codigos
        self.combobox_folha['values'] = codigos

    def filtrar_ids_folhas(self, event):
        texto_filtro = self.combobox_folha.get()
        if not texto_filtro:
            id_filtrados = self.id_folhas_original
        else:
            id_filtrados = [id for id in self.id_folhas_original if
                            texto_filtro.lower() in id.lower()]
        self.combobox_folha['values'] = id_filtrados
        print(f' --> Filtrando por: {texto_filtro}')
        print(f' --> Folhas disponíveis: {len(self.combobox_folha["values"])}')
        print(delimt)
        if not id_filtrados:
            print(f' --> Nenhum valor encontrado para: {texto_filtro}')
            print(f' IDs disponíveis: {self.id_folhas_original}')
            print('')
            self.combobox_folha['values'] = self.id_folhas_original

    # ---------------------------- Métodos ------------------------------------
    def selecionar_carta_postgres(self, escala):
        try:
            print('')
            print(' --------- Selecionando Carta Postgres ---------')
            carta = reverse_meta_cartas[escala]
            self.cartas = self.admin_folhas.seleciona_escala_postgres(carta)
            if self.cartas:
                self.atualizar_combobox_folha()
            else:
                print(f' --> Nenhuma folha encontrada para a escala: {escala}')

            return self.cartas

        except Exception as e:
            print('')
            print(' --> SeletorFolhas.selecionar_carta_postgres Falhou')
            print(f' !ERROR!: {e}')
            print('Parâmetros:')
            print(f' --> escala: {escala}')
            print(f' --> carta: {carta}')
            print(f' --> self.cartas: {len(self.cartas)}')
            return None

    def selecionar_carta_gpkg(self, escala):
        try:
            carta = reverse_meta_cartas[escala]
            self.cartas = self.admin_folhas.seleciona_escala_gpkg(carta)
            self.atualizar_combobox_folha()
            return self.cartas

        except Exception as e:
            print('')
            print(' --> SeletorFolhas.selecionar_carta_gpkg Falhou')
            print(f' !ERROR!: {e}')
            print('Parâmetros:')
            print(f' --> escala: {escala}')
            print(f' --> carta: {carta}')
            print(f' --> self.cartas: {len(self.cartas)}')

    # ---------------------------- Métodos ------------------------------------
    def define_area_de_estudo(self) -> Dict:
        plot_folhas = PlotFolhas(self)
        combobox_values = self.combobox_folha['values']
        if not combobox_values:
            print(f' --> COMBOBOX_VALUES: {combobox_values}')
            print(f' --> IDs disponíveis: {self.id_folhas_original}\n')
        print(f' --> Combobox_values: {combobox_values}')
        print(f' -> {type(combobox_values)}')
        print(f' --> self.cartas: {len(self.cartas)}')

        if isinstance(combobox_values, str):
            print(' --> Combobox_values é uma string')
            combobox_values = [combobox_values]
        elif isinstance(combobox_values, (tuple)):
            print(' --> Combobox_values é uma tupla')
            print(' --> Convertendo para lista')
            combobox_values = list(combobox_values)
        elif isinstance(combobox_values, (list)):
            print(' --> Combobox_values é uma lista')

        try:
            for codigo in combobox_values:
                self.folhas_estudo[codigo] = self.cartas[codigo]
            print(f' --> {len(self.folhas_estudo)} Folhas de Estudo')
            plot_folhas.plot_folha_estudo()
            return self.folhas_estudo

        except Exception as e:
            print('')
            print(' --> SeletorFolhas.define_area_de_estudo falhou!')
            print(f' !ERROR!: {e}')

    def old_adicionar_folha_estudo(self):
        self.area_de_estudo = getattr(self, 'area_de_estudo', [])
        try:
            print(' Executando SeletorFolhas.adicionar_folha_estudo')
            print(delimt)
            id_folha_estudo = self.combobox_folha.get()
            print(f' --> ID Folha de Estudo: {id_folha_estudo}')
            if any(id_folha_estudo == folha['codigo'].values[0] for folha in
                   self.area_de_estudo):
                print(f' --> Folha já adicionada: {id_folha_estudo} à lista')
                print('')
                return

            folha_estudo = self.admin_folhas.define_area_de_estudo(
                id_folha_estudo)
            self.area_de_estudo.append(folha_estudo)
            # ------------------- Prints
            print(f' --> Folha adicionada: {id_folha_estudo} à lista')
            n = len(self.area_de_estudo)
            print(f' --> Área de estudo com: {n} folha(s)')
            for folha in self.area_de_estudo:
                print(f'    --> ID: {folha.id_folha.values[0]}')
                print(f'    --> Poligono: {folha.geometry.bounds.values[0]}')
            print('')

        except Exception as e:
            print('')
            print(' --> SeletorFolhas.adicionar_folha_estudo falhou!')
            print(f' !EERRO!: {e}')
            print('Parâmetros:')
            print(f' --> id_folha_estudo: {id_folha_estudo}')
            print(f' --> self.area_de_estudo: {len(self.area_de_estudo)}')
            print('')

    def determine_folha_clicada(self, ax_x, ax_y):
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dicionarioFolhas.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folhaEstudo = self.dicionarioFolhas.carta_1kk.loc[id]

        return folhaEstudo

    def on_canvas_click(self, click_event):
        x, y = self.ax.transData.inverted().transform((click_event.x,
                                                       click_event.y))
        print('')
        print('########### Evento de Click no Canvas ###########')
        print(f' --> Coords: {x, y}')
        self.folhaEstudo = self.determine_folha_clicada(x, y)
        print(f' --> Folha clicada: {self.folhaEstudo.id_folha}')
        print('======================================================')
        print('')
        if self.folhaEstudo is not None:
            self.atualizarFolhaEstudo(self.folhaEstudo)
            # Atualizar Label Folha de Estudo
            self.frameSeletor.atualizarLabelFolhaEstudo(
                self.folhaEstudo.id_folha)
            self.interface.plotFolhas.plot_folha_estudo()
