# -*- coding: utf-8 -*-


def classFactory(iface):
    from .plugin import PreditorTerritorialMvpPlugin

    return PreditorTerritorialMvpPlugin(iface)
