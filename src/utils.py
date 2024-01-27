# funções e variáveis utilitárias podem ser adicionadas aqui conforme necessário

# Configura diretório da base de dados
def set_gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/database/'

        path : caminho até o  arquivo desejado
    '''
    gdb = '/home/ggrl/database/' + path
    return gdb
