# Autor: Gabriel Góes Rocha de Lima
# Data: 2024-02-04
# Descrição: Classe para plotar as folhas de estudo no canvas.

# ---------- imports
import shapely

# from utils import plotar

# -----------------------------------------------------------------------------


class PlotFolhas:
    # Método para determinar qual folha foi clicada por contains x, y
    def __init__(self, dicionarioFolhas, seletorFolhas, frameSeletor, ax):
        self.dicionarioFolhas = dicionarioFolhas
        self.seletorFolhas = seletorFolhas
        self.frameSeletor = frameSeletor
        self.ax = ax
        self.folhaEstudo = None

    def determine_folha_clicada(self, ax_x, ax_y):
        click = shapely.geometry.Point(ax_x, ax_y)
        for id, poly in self.dicionarioFolhas.carta_1kk.iterrows():
            if poly.geometry.contains(click):
                break
        folhaEstudo = self.dicionarioFolhas.carta_1kk.loc[id]

        return folhaEstudo

    # Método para ver click no canvas
    def on_canvas_click(self, event):
        '''
        Evento de click no canvas.
        '''
        # geographic coordinates from the click of mouse button
        x, y = self.ax.transData.inverted().transform((event.x, event.y))
        print('')
        print('########### Evento de Click no Canvas ###########')
        print(f' --> Coords: {x, y}')
        self.folhaEstudo = self.determine_folha_clicada(x, y)
        print(f' --> Folha clicada: {self.folhaEstudo.id_folha}')
        print('======================================================')
        print('')
        if self.folhaEstudo is not None:
            self.seletorFolhas.atualizarFolhaEstudo(self, self.folhaEstudo)
            # Atualizar Label Folha de Estudo
            self.frameSeletor.atualizarLabelFolhaEstudo(
                self.folhaEstudo.id_folha)


'''
    # Função para plotar a folha de estudo com folhas de ids contidos
    def plotAreaEstudo(self):
        Método para reconhecer o dicionariofolhas e plotar as folhas no
        canvas.

        #
        folhas = self.dicionarioFolhas.dicionarioFolhas
        carta = self.seletorFolhas.carta_selecionada
        print(f'Folhas: {folhas}')
        print(f'Carta: {carta}')
        print('======================================================')
        map, ax = plotar(folhas, carta)
        canvas = FigureCanvasTkAgg(map, master=self.canvas)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
        # ------------------- Toolbar - Plot Frame
        toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
        toolbar.update()
        toolbar.grid(row=1, column=0, padx=0, pady=0)
        canvas.get_tk_widget().grid(row=0, column=0, padx=0, pady=0)
        # ------------------- Evento de Click no Canvas
        map.canvas.mpl_connect('button_press_event', self.on_canvas_click)
'''
