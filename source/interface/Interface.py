# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# sourcuce/interface/Interface.py
# # ------------------------------ IMPORTS ------------------------------------
from AbrirFolhas import AbrirFolhas
from ManipulaFolhas import ManipularFolhas
from FrameSeletor import FrameSeletor
from utils import delimt

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------


# ------------------------------ INTERFACE ------------------------------------
class PreditorTerraUI:
    '''
        ======================================================
                      Interface do Preditor Terra
        ======================================================
    Esta Classe é responsável por criar a interface do Preditor Terra.
    '''
    # Construtor da classe PreditorTerra

    def __init__(self, root):
        print('')
        print('======================================================')
        print('              Interface do Preditor Terra             ')
        print('======================================================')
        # ---------------- Configuração do estilo da interface
        self.root = root
        self.setup_core()
        self.setup_style()
        self.setup_ui()
        print(delimt)

    # ---------------------------- Métodos ------------------------------------
    # Instancia as classes Core do Preditor Terra
    def setup_core(self):
        '''
        Método para  intanciar as classes responsáveis pelas
        lógicas de negócios
        '''
        # Instanciando AbrirFolhas
        self.admin_folhas = AbrirFolhas()
        self.manipula_folhas = ManipularFolhas(self.admin_folhas.dic_folhas)

    # método para executar as funções de configuração da interface
    def setup_ui(self):
        '''
        Método para configurar a interface do Preditor Terra e instanciar
        as classes reponsáveis pelas lógicas de interface.
        '''
        self.root.title('Preditor Terra')
        self.root.geometry('1440x900')
        # Label do topo - PREDITOR TERRA --------------------------------------
        label_root = tk.Label(self.root, text='Preditor Terra',
                              font=('SourceCodePro', 12, 'bold'),
                              relief=tk.GROOVE, bd=2)
        # Centraliza label Root no topo central do ROOT
        label_root.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        label_root.config(bg='black', fg='white')
        # ------------------- Main Frame
        self.main_frame = ttk.Frame(self.root, width=1420, height=880,
                                    relief=tk.GROOVE, style="Custom.TFrame")
        self.main_frame.grid(row=1, column=0, padx=0, pady=0, sticky='nsew')
        # ------------------- Seletor de Folhas - Frame
        self.frame_seletor = FrameSeletor(self.admin_folhas,
                                          self.main_frame,
                                          self.style)

    # Configura estilo do root para darkmode
    def setup_style(self):
        self.root.configure(bg='black')
        self.style = ttk.Style()
        self.style.configure("Custom.TFrame", background="black",
                             foreground="white")
        self.style.configure("Custom.TButton", background="black",
                             foreground="white")
        self.style.configure("Custom.TCombobox",
                             background="gray", foreground="black",
                             selectbackground="lightgray",
                             selectforeground="black", box="lightgray",
                             font=('SourceCodePro', 12, 'bold'))


# ---------------------------------------------------------------------------
# Define um método para iniciar o PreditorTerrraUI dentro de um ipython para
# Testar e ter acesso aos métodos e objetos desta classe.
def test_start(className='Preditor_Terra'):
    '''
    Função para iniciar o PreditorTerraUI dentro de um ipython.
    '''
    root = tk.Tk(className=className)
    app = PreditorTerraUI(root)
    return app, root


# ----------------------------- MAINLOOP
def start(className='Preditor_Terra'):
    '''
    Função principal para executar a interface do Preditor Terra.
    '''
    root = tk.Tk(className=className)
    app = PreditorTerraUI(root)
    root.mainloop()
    print(' Interface do Preditor Terra encerrada.')
    return app


# Inicialização do aplicativo
if __name__ == "__main__":
    start()
