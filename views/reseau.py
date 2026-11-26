import math

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

import ui_state
from svn_core.model import CATEGORIES as CATEGORIES_ORDER

STEP = 3
p = ui_state.project()
res, _ = ui_state.results()
ui_state.header(STEP, "Le réseau est dessiné automatiquement à partir de vos données. Le projet central "
                "est au centre ; l'épaisseur d'une flèche suit son score. Molette de la souris pour zoomer, "
                "glisser pour déplacer, double-clic pour recentrer.")

if not p.stakeholders:
    ui_state.empty_state("Aucune partie prenante pour l'instant.", ui_state.STEPS[0][0],
                         "Importer des données ou charger un exemple")
    ui_state.footer_nav(STEP)
    st.stop()

# Couleurs adaptées au thème clair ou sombre de l'application.
dark = getattr(getattr(st.context, "theme", None), "type", "light") == "dark"
TEXT = "#f2f4f7" if dark else "#14202c"
LABEL_BG = "rgba(38,39,48,0.92)" if dark else "rgba(255,255,255,0.92)"
LABEL_BORDER = "#4a5361" if dark else "#d5dce2"
EDGE = "#7fb6c9" if dark else "#5b8fa3"
MUTED = "#3d4450" if dark else "#d5dce2"
ACCENT = "#f0a35e" if dark else "#d58a45"
NODE_LINE = "#0e1117" if dark else "#ffffff"
GRID = "rgba(255,255,255,0.05)" if dark else "rgba(20,32,44,0.045)"
CATEGORY_COLORS = {"Technologique": "#637fa9", "Économique": "#d58a45", "Social": "#bf6573",
                   "Environnemental": "#2b967f", "Performance": "#298ca6", "Gestion": "#8059b9",
                   "Autre": "#8a96a3"}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def initials(name: str) -> str:
    words = [w for w in name.replace("-", " ").split() if w[:1].isalnum()]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return (name.strip()[:2] or "?").capitalize()


graph_col, ctrl_col = st.columns([3, 1], gap="large")
with ctrl_col:
    with st.container(border=True):
        st.markdown("**Affichage**")
        layout = st.radio("Disposition", ["Projet au centre", "Automatique"], key="net_layout",
                          help="« Automatique » place les nœuds très liés près les uns des autres.")
        edge_color = st.radio("Couleur des flèches", ["Par catégorie", "Par origine", "Uniforme"],
                              key="net_edge_color", horizontal=False,
                              help="« Par origine » reprend la couleur de la partie prenante qui "
                                   "fournit la valeur.")
        show_scores = st.toggle("Scores sur les flèches", value=True, key="net_scores")
    with st.container(border=True):
        st.markdown("**Mettre en évidence**")
        mode = st.radio("Élément", ["Rien", "Un cycle", "Une partie prenante"], key="net_mode",
                        label_visibility="collapsed")
        highlight_flows: set[str] = set()
        highlight_nodes: set[str] = set()
        if mode == "Un cycle":
            if res.cycles:
                i = st.selectbox("Cycle", range(min(50, len(res.cycles))),
                                 format_func=lambda k: f"n° {k + 1} · score {ui_state.fmt(res.cycles[k].score)}")
                c = res.cycles[i]
                highlight_flows = {f.id for f in c.flows}
                highlight_nodes = set(c.nodes)
                st.caption(" → ".join(p.name_of(n) for n in c.nodes))
            else:
                st.caption("Aucun cycle dans ce réseau.")
        elif mode == "Une partie prenante":
            sid = st.selectbox("Partie prenante", [s.id for s in p.stakeholders], format_func=p.name_of)
            highlight_flows = {f.id for f in p.valid_flows() if sid in (f.source, f.target)}
            highlight_nodes = {sid}
            st.caption(f"{sum(f.source == sid for f in p.valid_flows())} flux émis · "
                       f"{sum(f.target == sid for f in p.valid_flows())} flux reçus")

G = nx.MultiDiGraph()
G.add_nodes_from(s.id for s in p.stakeholders)
for f in p.valid_flows():
    G.add_edge(f.source, f.target, key=f.id)

others = [s.id for s in p.stakeholders if s.id != p.focal]
if layout == "Projet au centre" and p.focal:
    pos = {p.focal: (0.0, 0.0)}
    for i, sid in enumerate(others):
        a = 2 * math.pi * i / max(1, len(others)) + math.pi / 2
        pos[sid] = (math.cos(a), math.sin(a))
else:
    pos = nx.spring_layout(nx.Graph(G), seed=42)
    pos = {k: (float(v[0]), float(v[1])) for k, v in pos.items()}

fig = go.Figure()
NODE_R = 0.1  # rayon visuel d'un nœud, en unités du graphique
pair_count: dict = {}
hover_x, hover_y, hover_t, hover_c = [], [], [], []
active = bool(highlight_flows) or bool(highlight_nodes)
colors = {s.id: s.color for s in p.stakeholders}
used_categories: list[str] = []


def flow_color(f) -> str:
    if edge_color == "Par catégorie":
        return CATEGORY_COLORS.get(f.category, CATEGORY_COLORS["Autre"])
    if edge_color == "Par origine":
        return colors.get(f.source, EDGE)
    return EDGE


for f in p.valid_flows():
    (x0, y0), (x1, y1) = pos[f.source], pos[f.target]
    k = pair_count.get((f.source, f.target), 0)
    pair_count[(f.source, f.target)] = k + 1
    # Courbe de Bézier quadratique : sépare les flux aller/retour et les flux parallèles.
    dx, dy = x1 - x0, y1 - y0
    norm = math.hypot(dx, dy) or 1
    off = 0.14 * (1 + k) * norm
    cx, cy = (x0 + x1) / 2 - dy / norm * off, (y0 + y1) / 2 + dx / norm * off
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1,
            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1) for t in [i / 60 for i in range(61)]]
    pts = [q for q in pts if math.hypot(q[0] - x0, q[1] - y0) > NODE_R
           and math.hypot(q[0] - x1, q[1] - y1) > NODE_R * 1.2]
    if len(pts) < 2:
        continue
    on = f.id in highlight_flows
    base = flow_color(f)
    if f.category not in used_categories:
        used_categories.append(f.category)
    if on:
        color = ACCENT
    elif active:
        color = MUTED
    else:
        color = rgba(base, 0.78)
    width = 1.2 + 3.8 * float(f.score) + (1.5 if on else 0)
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    if on:  # halo lumineux sous la flèche mise en évidence
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                                 line=dict(color=rgba(ACCENT, 0.25), width=width + 8, shape="spline")))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                             line=dict(color=color, width=width, shape="spline")))
    (ax, ay), (ex, ey) = pts[-3], pts[-1]
    fig.add_annotation(x=ex, y=ey, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=max(0.9, 2.4 / width),
                       arrowwidth=width, arrowcolor=color, text="")
    mx, my = pts[len(pts) // 2]
    hover_x.append(mx); hover_y.append(my); hover_c.append(base)
    hover_t.append(f"<b>{f.name}</b><br>{p.name_of(f.source)} → {p.name_of(f.target)}"
                   f"<br>score {ui_state.fmt(f.score, 2)} · {f.category}")
    if show_scores and (not active or on):
        fig.add_annotation(x=mx, y=my, text=ui_state.fmt(f.score, 2), showarrow=False,
                           font=dict(size=10, color=TEXT, family="Inter, system-ui, sans-serif"),
                           bgcolor=LABEL_BG, bordercolor=rgba(base, 0.6) if not active else LABEL_BORDER,
                           borderwidth=1, borderpad=3)

# Zones de survol invisibles au milieu de chaque flèche.
fig.add_trace(go.Scatter(x=hover_x, y=hover_y, mode="markers", showlegend=False,
                         marker=dict(size=16, opacity=0), hovertext=hover_t, hoverinfo="text",
                         hoverlabel=dict(bgcolor=hover_c or None, font=dict(color="#ffffff"))))

# Nœuds : halo doux + disque coloré avec initiales + étiquette du nom.
sx = [pos[s.id][0] for s in p.stakeholders]
sy = [pos[s.id][1] for s in p.stakeholders]
size = [62 if s.id == p.focal else 46 for s in p.stakeholders]
dim = [active and s.id not in highlight_nodes for s in p.stakeholders]
fig.add_trace(go.Scatter(
    x=sx, y=sy, mode="markers", hoverinfo="skip", showlegend=False,
    marker=dict(size=[z + 18 for z in size],
                color=[rgba(ACCENT if s.id in highlight_nodes else s.color, 0.0 if d else 0.22)
                       for s, d in zip(p.stakeholders, dim)], line=dict(width=0))))
fig.add_trace(go.Scatter(
    x=sx, y=sy, mode="markers+text", hoverinfo="text",
    text=[initials(s.name) for s in p.stakeholders], textposition="middle center",
    textfont=dict(color="#ffffff", size=[15 if s.id == p.focal else 12 for s in p.stakeholders],
                  family="Inter, system-ui, sans-serif"),
    hovertext=[f"<b>{s.name}</b><br>{s.type}"
               + ("<br>projet central" if s.id == p.focal and s.type != "Projet central" else "")
               + f"<br>{sum(f.source == s.id for f in p.valid_flows())} flux émis · "
               f"{sum(f.target == s.id for f in p.valid_flows())} flux reçus"
               for s in p.stakeholders],
    hoverlabel=dict(bgcolor=[s.color for s in p.stakeholders], font=dict(color="#ffffff", size=13)),
    marker=dict(size=size, color=[s.color for s in p.stakeholders],
                opacity=[0.35 if d else 1 for d in dim],
                line=dict(color=[ACCENT if s.id in highlight_nodes else NODE_LINE
                                 for s in p.stakeholders],
                          width=[4 if s.id == p.focal or s.id in highlight_nodes else 2.5
                                 for s in p.stakeholders])),
    showlegend=False))
for s, d in zip(p.stakeholders, dim):
    x, y = pos[s.id]
    fig.add_annotation(x=x, y=y, yshift=-44 if s.id == p.focal else -36,
                       text=f"<b>{s.name}</b>" + (" ★" if s.id == p.focal else ""),
                       showarrow=False, opacity=0.5 if d else 1,
                       font=dict(size=12.5, color=TEXT, family="Inter, system-ui, sans-serif"),
                       bgcolor=LABEL_BG, bordercolor=rgba(s.color, 0.7), borderwidth=1.5, borderpad=4)

# Légende des catégories (traces vides, une par catégorie présente).
if edge_color == "Par catégorie":
    for cat in CATEGORIES_ORDER:
        if cat in used_categories:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=cat, hoverinfo="skip",
                                     line=dict(color=CATEGORY_COLORS.get(cat, EDGE), width=4)))

fig.update_layout(height=680, margin=dict(l=10, r=10, t=36, b=30),
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
                  hoverlabel=dict(font_size=13, bordercolor="rgba(0,0,0,0)"),
                  dragmode="pan", hovermode="closest", uirevision=f"{p.name}-{layout}",
                  legend=dict(orientation="h", x=0.5, xanchor="center", y=0, yanchor="top", font=dict(size=11),
                              bgcolor="rgba(0,0,0,0)", itemclick=False, itemdoubleclick=False),
                  xaxis=dict(range=[-1.4, 1.4], showgrid=True, gridcolor=GRID, zeroline=False,
                             showticklabels=False, ticks="", dtick=0.2, title=None),
                  yaxis=dict(range=[-1.32, 1.32], scaleanchor="x", showgrid=True, gridcolor=GRID,
                             zeroline=False, showticklabels=False, ticks="", dtick=0.2, title=None))
with graph_col:
    with st.container(border=True):
        st.plotly_chart(fig, use_container_width=True, theme=None, key="network_map",
                        config={"displaylogo": False, "scrollZoom": True, "doubleClick": "reset",
                                "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d",
                                                           "hoverClosestCartesian",
                                                           "hoverCompareCartesian",
                                                           "toggleSpikelines"],
                                "toImageButtonOptions": {"format": "png", "filename": "reseau_svn",
                                                         "scale": 2}})
    st.caption("★ = projet central. :material/mouse: Molette : zoom avant / arrière · glisser : "
               "déplacer · double-clic : revenir à la vue d'ensemble · icône appareil photo : "
               "enregistrer l'image en PNG.")

ui_state.footer_nav(STEP)
