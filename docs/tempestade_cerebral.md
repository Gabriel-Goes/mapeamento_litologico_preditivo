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



## Métodos Para Implementar

### Parser de 'LITOLOGIA' e 'LEGENDA'
    -> Um método que recebe uma 'str' os atributos que a contém.
    -> Pode ser usado para procurar geometrias que contêm um mineral
    -> Posso implementar algo como o Telescope LiveGrep

### Lógica de cores de mapas litológicos
    -> utilizar uma lógica de cores para escolher uma cor automaticamente \\
        baseado na 'SIGLA ID'
    -> SGB-CPRM tem um arquivo de estilo para QGIS, mas incomplete.
