# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# source/interface/SeletorFolhas.py
# Descrição: Classe para implementar métodos de seleção de folhas.
# -----------------------------------------------------------------------------
import shapely
from utils import reverse_meta_cartas, delimt
# Import python Dictionary
from typing import Dict


# ------------------------------ CLASSES ------------------------------------
class SeletorFolhas:
    '''
    Classe para implementar métodos de seleção de folhas.
        Será instanciado por FrameSeletor e utilizado para atualizar valores
        de escala e atualizar folha de estudo e gerar dicionário de folhas.
    '''

    def __init__(self,
                 combobox_cartas, combobox_folha,
                 admin_folhas):
        '''
        Construtor da classe SeletorFolhas.
        '''
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
    # Visualiza valor de Combobox Cartas
    def get_combobox_cartas(self):
        '''
        Método para visualizar valor de Combobox Cartas.
        '''
        print(f' --> Escala escolhida: {self.combobox_cartas.get()}')
        self.escala = self.combobox_cartas.get()

    # Evento de Combobox Cartas atualizado
    def evento_combobox_cartas(self, event):
        '''
        Evento de Combobox Cartas atualizado.
        '''
        self.get_combobox_cartas()
        # self.selecionar_carta_gpkg(self.escala)
        self.selecionar_carta_postgres(self.escala)

    # Atualiza valores de Combobox Folhas
    def atualizar_combobox_folha(self):
        '''
        Método para atualizar valores de Combobox Folhas.
        '''
        # Atualiza valores de Combobox Folhas
        folha_ids = list(self.cartas.keys())
        self.id_folhas_original = folha_ids
        self.combobox_folha['values'] = folha_ids

    # Filtra códigos de folhas com base no texto inserido
    def filtrar_ids_folhas(self, event):
        '''
        Método para filtrar códigos de folhas do combobox_folha com base no
        texto inserido.
        '''
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

    # Seleciona Folhas a partir das esclas disponíveis em meta_cartas
    def selecionar_carta_postgres(self, escala):
        '''
        Método para selecionar folhas a partir das escalas disponíveis em
        meta_cartas.
        '''
        try:
            print('')
            print(' --------- Selecionando Carta Postgres ---------')
            carta = reverse_meta_cartas[escala]
            self.cartas = self.admin_folhas.seleciona_escala_postgres(carta)
            self.atualizar_combobox_folha()
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

    # Seleciona Folhas a partir das esclas disponíveis em meta_cartas
    def selecionar_carta_gpkg(self, escala):
        '''
        Método para selecionar folhas a partir das escalas disponíveis em
        meta_cartas.
        '''
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

    # Define área de estudo
    def define_area_de_estudo(self) -> Dict:
        '''
        Método para definir a área de estudo.
        Cria um novo dicionário de folhas que representa a área de estudo
        Este dicionário contêm todas as folhas que compõem a área de estudo
        Com folha_id, geometry e epsg, escala
        Ele será formado a partir dos valores de combobox_folha
        Recebe:
            combobox_values: str - valores de combobox_folha
        Retorna:
            cartas_estudo: dicionário - dicionário de folhas que representa a
                área de estudo
        '''
        combobox_values = self.combobox_folha['values']
        try:
            for folha_id in combobox_values:
                self.folhas_estudo[folha_id] = self.cartas[folha_id]

            print(f' --> {len(self.folhas_estudo)} Folhas de Estudo')
            return self.folhas_estudo

        except Exception as e:
            print('')
            print(' --> SeletorFolhas.define_area_de_estudo falhou!')
            print(f' !ERROR!: {e}')
            print('Parâmetros:')
            print(f' --> combobox_values: {combobox_values}')
            print(f' --> self.cartas: {len(self.cartas)}')
            print('')

    # Adiciona folha de estudo à área de estudo
    def old_adicionar_folha_estudo(self):
        '''
        Método para adicionar folha de estudo à área de estudo.
        '''
        # Lista de área de estudo
        self.area_de_estudo = getattr(self, 'area_de_estudo', [])
        try:
            print(' Executando SeletorFolhas.adicionar_folha_estudo')
            print(delimt)
            id_folha_estudo = self.combobox_folha.get()
            print(f' --> ID Folha de Estudo: {id_folha_estudo}')
            if any(id_folha_estudo == folha['folha_id'].values[0] for folha in
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

    # Método para determinar folha clicada
    def determine_folha_clicada(self, ax_x, ax_y):
        '''
        Define qual folha foi clicada no canvas a partir das coordenadas ax_x e
        ax_y pelo método contains.
        '''
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dicionarioFolhas.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folhaEstudo = self.dicionarioFolhas.carta_1kk.loc[id]

        return folhaEstudo

    # Método para ver click no canvas
    def on_canvas_click(self, click_event):
        '''
        Evento de click no canvas.
        '''
        # geographic coordinates from the click of mouse button
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
