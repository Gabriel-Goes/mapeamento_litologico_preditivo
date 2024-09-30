# ./fonte/mapgeo/__init__.py
# Gabriel Góes

import os
import logging


def classFactory(iface):
    from .mapgeo import mapgeo
    return mapgeo(iface)


def setup_logging():
    """Configura o logger para o plugin, antes de qualquer execução."""
    print("Iniciando setup_logging...")
    log_dir = os.path.expanduser('~/logs')
    log_file = os.path.join(log_dir, 'mapgeo.log')

    print(f"Tentando criar o diretório de logs: {log_dir}")
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Configura o logger
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.info("Log iniciado com sucesso no __init__.py.")
        print("Log iniciado com sucesso!")
        return logger

    except Exception as e:
        # Se o log falhar, imprime no console
        print(f"Erro ao configurar o log: {e}")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao configurar o log no __init__.py. Log será impresso no console: {e}")
        print(f"Erro ao configurar o log: {e}")
        return logger

logger = setup_logging()
logger.info("Plugin mapgeo foi carregado com sucesso.")
print("Setup do log concluído.")
