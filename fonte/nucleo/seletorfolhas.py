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
#  Classe para implementar métodos de seleção de folhas.
#  Será instanciado por FrameSeletor e utilizado para atualizar valores
#  de escala e atualizar folha de estudo e gerar dicionário de folhas.


# ------------------------------ CLASSES ------------------------------------
class SeletorFolhas:

    # ---------------------------- Construtor ---------------------------------
    def __init__(self, combobox_cartas, combobox_folha, admin_folhas):
        logger.debug('-> Iniciando SeletorFolhas')
        try:
            self.combobox_folha = combobox_folha
            self.combobox_cartas = combobox_cartas
            self.admin_folhas = admin_folhas
            self.folhas_estudo = {}
        except Exception as e:
            print('SeletorFolhas falhou!', e)
            logger.error('SeletorFolhas falhou!', exc_info=True)
            logger.error(f'Parâmetros: combobox_cartas={combobox_cartas}, combobox_folha={combobox_folha}, admin_folhas={admin_folhas}')
            logger.error(delimt)

    # ---------------------------- Métodos ------------------------------------
    def get_combobox_cartas(self):
        logger.debug(f'Escala escolhida: {self.combobox_cartas.get()}')
        self.escala = self.combobox_cartas.get()

    def evento_combobox_cartas(self, event):
        self.get_combobox_cartas()
        logger.debug('Iniciando seleção da carta no PostgreSQL...')
        self.selecionar_carta_postgres(self.escala)

    def atualizar_combobox_folha(self):
        if self.cartas is not None:
            codigos = list(self.cartas.keys())
        else:
            logger.error("ERRO: 'SELF.CARTAS' É NONE")
        self.id_folhas_original = codigos
        self.combobox_folha['values'] = codigos
        logger.debug(f'Combobox atualizada com {len(codigos)} códigos de folhas')

    def filtrar_ids_folhas(self, event):
        texto_filtro = self.combobox_folha.get()
        if not texto_filtro:
            id_filtrados = self.id_folhas_original
        else:
            id_filtrados = [id for id in self.id_folhas_original if texto_filtro.lower() in id.lower()]

        self.combobox_folha['values'] = id_filtrados
        logger.debug(f'Filtrando por: {texto_filtro}. Folhas disponíveis: {len(id_filtrados)}')
        if not id_filtrados:
            logger.warning(f'Nenhum valor encontrado para: {texto_filtro}')
            logger.warning(f'IDs disponíveis: {self.id_folhas_original}')
            self.combobox_folha['values'] = self.id_folhas_original

    # ---------------------------- POSTGRES -----------------------------------
    def selecionar_carta_postgres(self, escala):
        try:
            logger.debug(' --------- Selecionando Carta Postgres ---------')
            carta = reverse_meta_cartas[escala]
            self.cartas = self.admin_folhas.seleciona_escala_postgres(carta)
            if self.cartas:
                logger.debug(f'{len(self.cartas)} folhas importadas para a escala {escala}')
                self.atualizar_combobox_folha()
            else:
                logger.warning(f'Nenhuma folha encontrada para a escala: {escala}')
            return self.cartas

        except Exception as e:
            print('SeletorFolhas.selecionar_carta_postgres Falhou!', e)
            logger.error('SeletorFolhas.selecionar_carta_postgres Falhou', exc_info=True)
            logger.error(f'Parâmetros: escala={escala}, carta={carta}')
            return None

    # ---------------------------- Define -------------------------------------
    def define_estudo(self) -> Dict:
        plot_folhas = PlotFolhas(self)
        combobox_values = self.combobox_folha['values']
        if not combobox_values:
            logger.warning(f' --> IDs disponíveis: {self.id_folhas_original}')
            return {}

        logger.debug(f' --> COMBOBOX_VALUES: {combobox_values}')
        logger.debug(f' --> self.cartas: {len(self.cartas)}')

        try:
            for codigo in combobox_values:
                self.folhas_estudo[codigo] = self.cartas[codigo]
            logger.debug(f'{len(self.folhas_estudo)} Folhas de Estudo adicionadas')
            plot_folhas.plot_folha_estudo()
            return self.folhas_estudo

        except Exception as e:
            print('SeletorFolhas.define_estudo falhou!', e)
            logger.error('SeletorFolhas.define_estudo falhou!', exc_info=True)

    # ---------------------------- Eventos de Click ---------------------------
    def determine_folha_clicada(self, ax_x, ax_y):
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dicionarioFolhas.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folhaEstudo = self.dicionarioFolhas.carta_1kk.loc[id]
        return folhaEstudo

    def on_canvas_click(self, click_event):
        x, y = self.ax.transData.inverted().transform((click_event.x, click_event.y))
        logger.debug('########### Evento de Click no Canvas ###########')
        logger.debug(f' --> Coords: {x, y}')
        self.folhaEstudo = self.determine_folha_clicada(x, y)
        logger.debug(f' --> Folha clicada: {self.folhaEstudo.id_folha}')
        if self.folhaEstudo is not None:
            self.atualizarFolhaEstudo(self.folhaEstudo)
            self.frameSeletor.atualizarLabelFolhaEstudo(self.folhaEstudo.id_folha)
            self.interface.plotFolhas.plot_folha_estudo()
