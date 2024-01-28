# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
#
# # ------------------------------ IMPORTS ------------------------------------
# Script de testes de classes e funções
from utils import list_files, set_gdb
from DicionarioFolhas import DicionarioFolhas
from ManipulaFolhas import ManipularFolhas

# ------------------------------ TESTES ------------------------------------
# Teste da classe DicionarioFolhas
dfc = DicionarioFolhas()
folhas_100k = dfc.gera_dicionario_de_folhas(carta='100k', id_folha='SF23-YA')

print(' ------------------------------ ')
print(f'Folhas 1:100.000 -> {len(folhas_100k)}')

# identifica quais dados disponíveis em geof
list_geof = list_files(set_gdb('geof'))
print(f'Lista de dados: {list_geof}')
print(' ------------------------------ ')

# Teste da classe ManipularFolhas
mf_100k = ManipularFolhas(folhas_100k)

mf_100k.adicionar_geofisica(gama_xyz='gama_line_1105',
                            mag_xyz='mag_line_1105',
                            extend_size=0.1)
