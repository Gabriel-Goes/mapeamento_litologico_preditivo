# make_figs_pygmt.py
import os
import pygmt

OUTDIR = "figs"
os.makedirs(OUTDIR, exist_ok=True)

# --- (A) Estudo do artigo base: Jilinbaolige (coordenadas verificadas) ---
# Fonte: Mindat (Jilinbaolige Ag-Au deposit) 45.92000 N, 118.00000 E
JLON, JLAT = 118.00000, 45.92000

def fig1_world_loc():
    fig = pygmt.Figure()
    fig.coast(region="g", projection="W12c",
              land="gray90", water="white", shorelines="0.5p,black",
              borders="1/0.5p,black", frame="afg")
    fig.plot(x=JLON, y=JLAT, style="a0.5c", pen="1p,black", color="red")
    fig.text(x=JLON+10, y=JLAT-3, text="Jilinbaolige", font="10p,Helvetica-Bold,black")
    fig.savefig(os.path.join(OUTDIR, "fig1_world_loc.png"), dpi=300)

def fig2_inner_mongolia_zoom():
    # janela regional ~6°x4° ao redor do ponto (ajuste se quiser)
    dx, dy = 6, 4
    region = [JLON - dx, JLON + dx, JLAT - dy, JLAT + dy]
    fig = pygmt.Figure()
    fig.coast(region=region, projection="M12c",
              land="gray95", water="white", shorelines="0.75p,black",
              borders="1/0.75p,black", frame=["WSen", "af"])
    fig.grid(frame="afg", pen="0.25p,gray70")
    fig.plot(x=JLON, y=JLAT, style="a0.5c", pen="1p,black", color="red")
    # Rosa-dos-ventos e escala gráfica simples
    fig.basemap(compass="jTR+w1.5c+o0.4c/0.4c+f", map_scale="jBL+w200k+o0.6c/0.6c+f")
    fig.savefig(os.path.join(OUTDIR, "fig2_inner_mongolia_zoom.png"), dpi=300)

# --- (B) Área-alvo genérica (edite o retângulo AOI conforme o seu estudo) ---
# Exemplo inicial (BR centro-leste): lonW, lonE, latS, latN
AOI = [-56.0, -46.0, -23.0, -14.0]  # <<< EDITE ESTES LIMITES PARA A SUA ÁREA >>>

def fig3_aoi_generica():
    lonW, lonE, latS, latN = AOI
    # Região de plotagem: o retângulo + margem
    margin = 3
    region = [lonW - margin, lonE + margin, latS - margin, latN + margin]

    fig = pygmt.Figure()
    fig.coast(region=region, projection="M12c",
              land="gray95", water="white", shorelines="0.5p,black",
              borders="1/0.5p,black", frame=["WSen", "af"])
    fig.grid(frame="afg", pen="0.25p,gray70")

    # Retângulo do AOI
    xs = [lonW, lonE, lonE, lonW, lonW]
    ys = [latS, latS, latN, latN, latS]
    fig.plot(x=xs, y=ys, pen="1.2p,red")

    fig.text(x=(lonW+lonE)/2, y=latN+0.7, justify="CT",
             text="Área de Estudo (AOI)", font="10p,Helvetica-Bold,red")
    fig.basemap(compass="jTR+w1.5c+o0.4c/0.4c+f", map_scale="jBL+w200k+o0.6c/0.6c+f")
    fig.savefig(os.path.join(OUTDIR, "fig3_aoi_generica.png"), dpi=300)

if __name__ == "__main__":
    fig1_world_loc()
    fig2_inner_mongolia_zoom()
    fig3_aoi_generica()
    print(f"[OK] Figuras salvas em: {OUTDIR}/")
