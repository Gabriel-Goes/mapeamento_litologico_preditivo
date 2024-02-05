import folium


def criar_mapa_folium():
    '''
    Cria um mapa do Brasil usando a biblioteca Folium.
    '''
    m = folium.Map(
        location=[-15.77972, -47.92972], zoom_start=4,
        tiles='OpenStreetMap',  # 'Stamen
        attr='Map data @ <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ')
    mapa_html = '../utils/mapa_html.html'
    m.save(mapa_html)

    return mapa_html


if __name__ == '__main__':
    criar_mapa_folium()
