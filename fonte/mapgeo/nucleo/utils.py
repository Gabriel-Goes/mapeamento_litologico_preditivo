import os
import matplotlib.pyplot as plt
import pygmt
import geopandas as gpd


# funções e variáveis úteis podem ser adicionadas aqui conforme necessário
# Configura diretório da base de dados

'''
        # Atualizar labelFolhaEstudo
        self.frameSeletor.atualizarLabelFolhaEstudo(self.folhaEstudo)
'''

# Configura delimitador para prints de relatorio de execução
delimt = '------------------------------------------------------\n'


# configura PostgreSQL para conexão
gdb_url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/geodatabase'


def set_db(path=''):
    return '/home/database/' + path


# Lista os arquivos de um diretório
def list_files(path):
    return os.listdir(path)


# Criar gerador de intervalos
def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step


def get_epsg(folha_id):
    if folha_id.startswith('S'):
        return '327' + folha_id[2:4]
    else:
        return '326' + folha_id[2:4]


# define geometria do Brasil
ibge = set_db('shapefiles/IBGE/')
regioes = gpd.read_file(ibge + 'ANMS2010_06_grandesregioes.shp')
brasil = regioes.unary_union


meta_cartas = {
    '1kk': {'escala': '1:1.000.000',
            'incrementos': (4, 6),
            'codigos': ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                        'H', 'I', 'J', 'K', 'L', 'M', 'N',
                        'O', 'P', 'Q', 'R', 'S', 'T']},
    '500k': {'escala': '1:500.000',
             'incrementos': (2, 3),
             'codigos': [['V', 'Y'], ['X', 'Z']]},
    '250k': {'escala': '1:250.000',
             'incrementos': (1, 1.5),
             'codigos': [['A', 'C'], ['B', 'D']]},
    '100k': {'escala': '1:100.000',
             'incrementos': (0.5, 0.5),
             'codigos': [['I', 'IV'], ['II', 'V'], ['III', 'VI']]},
    '50k': {'escala': '1:50.000',
            'incrementos': (0.25, 0.25),
            'codigos': [['1', '3'], ['2', '4']]},
    '25k': {'escala': '1:25.000',
            'incrementos': (0.125, 0.125),
            'codigos': [['NW', 'SW'], ['NE', 'SE']]}
}

reverse_meta_cartas = {meta_cartas[k]['escala']: k for k in meta_cartas}
