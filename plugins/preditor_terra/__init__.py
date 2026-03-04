# -*- coding: utf-8 -*-

def classFactory(iface):
    from .preditor_terra_plugin import PreditorTerraPlugin
    return PreditorTerraPlugin(iface)

