# Pensamentos Sobre o Projeto
## Interface Gráfica Interagindo Com Código Fonte

Aplicativo
│
├── DicionarioFolhas
│   ├── bbox
│   ├── carta_1kk
│   ├── filtgeo
│   ├── filtrar_mc_exato()
│   └── gera_dicionario_folhas()
│
├── FolhaEstudo = Nada
│
├── PlotFrame
│   ├── MainFrame
│   ├── SeletorFolhas
│   ├── FolhaEstudo
│   ├── DicF
│   ├── Canvas
│   ├── Ax
│   ├── Style
│   ├── determine_folha_clicada()
│   ├── on_canvas_click()
│   └── plot_frame()
│
├── Root (Tkinter Root)
│
├── SeletorFolhas
│   ├── MainFrame
│   ├── FrameFolhaEstudo
│   ├── SeletorFolhasFrame
│   ├── ComboboxCarta
│   ├── ComboboxFolha
│   ├── CartaSelecionada
│   ├── DicionarioFolhas
│   ├── Dicionario
│   ├── FolhaEstudo
│   ├── Style
│   ├── criar_seletor_folhas()
│   ├── e_gerar_dicionario_folhas()
│   ├── atualizar_valores_folhas()
│   └── atualizar_folha_estudo()
│
│── Style (Tkinter Style)
│
└── setup_ui() (chama

    - aplicativo
        - dicionario_folhas
            - bbox
            - carta_1kk
            - filtgeo
            - filtrar_mc_exato()
            - gera_dicionario_folhas()
        - folha_estudo = Nada
        - plot_frame
            - main_frame
            - seletor_folhas
            - folha_estudo
            - dic_fCopy
            - canvas
            - ax
            - style
            - determine_folha_clicada()
            - on_canvas_click()
            - plot_frame()
        - root(TKINTER ROOT)
        - seletor_folhas
                - main_frame
                - frame_folha_estudo
                - seletor_folhas_frame
                - combobox_carta
                - combobox_folha
                - carta_selecionada
                - dicionario_folhas
                - dicionario
                - folha_estudo
                - style
                - criar_seletor_folhas()
                - e_gerar_dicionario_folhas()
                - atualizar_valores_folhas()
                - atualizar_folha_estudo()
        - style(TKINTER STYLE)
        - setup_ui() (CHAMA AS FUNÇÕES ACIMA)
