import os


# funções e variáveis úteis podem ser adicionadas aqui conforme necessário
# Configura diretório da base de dados
def set_gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/database/'
        # $HOME/database/

        path : caminho até o  arquivo desejado
    '''
    gdb = '/home/ggrl/database/' + path
    return gdb


# Lista os arquivos de um diretório
def list_files(path):
    '''
    Lista os arquivos de um diretório
    '''
    return os.listdir(path)


# Criar gerador de intervalos
def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step
