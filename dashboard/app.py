import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import sample_colorscale
from sqlalchemy import URL, create_engine

st.set_page_config(page_title="Preço da Gasolina no Brasil", page_icon="⛽", layout="wide")

BASE = Path(__file__).parent

# Paleta
BLUE = "#3b82f6"
GREEN = "#22c55e"
TEAL = "#2dd4bf"
ORANGE = "#f97316"
PURPLE = "#8b5cf6"
CYAN = "#22d3ee"
MUTED = "#94a3b8"
GRID = "#16233d"


# ---------------------------------------------------------------- Ícones (SVG)
def icon(name, color="currentColor", size=22, stroke=2):
    paths = {
        "fuel": '<line x1="3" x2="15" y1="22" y2="22"/><line x1="4" x2="14" y1="9" y2="9"/>'
                '<path d="M14 22V4a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v18"/>'
                '<path d="M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 2 2a2 2 0 0 0 2-2V9.83a2 2 0 0 0-.59-1.42L18 5"/>',
        "bars": '<rect x="4" y="13" width="3.5" height="8" rx="1"/><rect x="10.25" y="8" width="3.5" height="13" rx="1"/>'
                '<rect x="16.5" y="3" width="3.5" height="18" rx="1"/>',
        "down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
        "trend": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
        "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
        "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        "chart": '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/>',
        "map": '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/>'
               '<line x1="15" x2="15" y1="6" y2="21"/>',
        "doc": '<rect x="4" y="3" width="16" height="18" rx="2"/><line x1="8" x2="16" y1="9" y2="9"/>'
               '<line x1="8" x2="16" y1="13" y2="13"/><line x1="8" x2="13" y1="17" y2="17"/>',
        "gear": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73'
                'l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38'
                'a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18'
                'a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08'
                'a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08'
                'a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
        "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/>'
                    '<line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
        "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
                  '<path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
                  '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
                  '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
        "sliders": '<line x1="3" x2="21" y1="6" y2="6"/><line x1="3" x2="21" y1="18" y2="18"/>'
                   '<circle cx="8" cy="6" r="2.5"/><circle cx="15" cy="18" r="2.5"/><line x1="3" x2="21" y1="12" y2="12"/>',
        "bulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
                '<path d="M9 18h6"/><path d="M10 22h4"/>',
        "bar_up": '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="9" width="3" height="9"/>'
                  '<rect x="17" y="6" width="3" height="12"/>',
    }
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>')


def br(v, casas=2):
    return f"{v:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------- Dados (camada gold da pipeline-combustiveis)
MESES = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]


def data_br(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


@st.cache_resource
def engine():
    url = URL.create("postgresql+psycopg2", username=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                     host=os.environ.get("DB_HOST", "postgres"), port=int(os.environ.get("DB_PORT", 5432)),
                     database=os.environ.get("DB_NAME", "analytics"))
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=3600)  # a pipeline roda 1x por semana; 1 h de cache é suficiente
def carregar():
    with engine().connect() as c:
        semanal = pd.read_sql("SELECT semana, nivel, codigo, nome, preco_medio FROM gold.preco_semanal",
                              c, parse_dates=["semana"])
        resumo = pd.read_sql("SELECT * FROM gold.resumo", c, parse_dates=["semana_atual"])
    return semanal, resumo


try:
    SEMANAL, RESUMO = carregar()
except Exception as e:  # banco fora do ar ou pipeline ainda não rodou
    st.error(f"Não foi possível ler os dados da pipeline (gold.preco_semanal / gold.resumo): {e}")
    st.stop()

UFS = RESUMO[RESUMO.nivel == "uf"].sort_values("preco_atual", ascending=False).reset_index(drop=True)
REG = RESUMO[RESUMO.nivel == "regiao"].sort_values("preco_atual", ascending=False)
BR = RESUMO[RESUMO.nivel == "pais"].iloc[0]
SEMANA = BR.semana_atual
MAIOR, MENOR = UFS.iloc[0], UFS.iloc[-1]
ROTULO = lambda r: f"{r.nome} ({r.codigo})"  # noqa: E731

# Série semanal do Brasil, para comparar com ~1 mês antes
SERIE_BR = SEMANAL[SEMANAL.nivel == "pais"].set_index("semana")["preco_medio"].sort_index()
MES_ANTERIOR = SERIE_BR.asof(SEMANA - pd.Timedelta(weeks=4))
VAR_MES = (BR.preco_atual / MES_ANTERIOR - 1) * 100

# Escala de cor do mapa (azul = mais barato, laranja = mais caro)
ESCALA = [[0, "#2563eb"], [0.5, "#22c55e"], [1, "#f97316"]]
P_MIN, P_MAX = UFS.preco_atual.min(), UFS.preco_atual.max()


def cor_preco(v):
    return sample_colorscale(ESCALA, [(v - P_MIN) / (P_MAX - P_MIN)])[0]


@st.cache_data
def geojson_brasil():
    return json.loads((BASE / "brazil-states.geojson").read_text())


# ---------------------------------------------------------------- CSS
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stApp {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: radial-gradient(1200px 500px at 70% -10%, #0f2244 0%, #060d1c 60%) #060d1c; }}
header[data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display:none !important; }}
.block-container {{ padding: 1.2rem 1.6rem 1rem 6.2rem !important; max-width: 100% !important; }}
div[data-testid="stVerticalBlock"] {{ gap: .9rem; }}
div[data-testid="stHorizontalBlock"] {{ gap: .9rem; }}

/* trilho lateral */
.rail {{ position:fixed; left:0; top:0; bottom:0; width:66px; background:#050b18; border-right:1px solid #111d33;
         display:flex; flex-direction:column; align-items:center; gap:26px; padding-top:22px; z-index:1000; }}
.rail .it {{ color:#64748b; width:38px; height:38px; display:flex; align-items:center; justify-content:center; border-radius:10px; }}
.rail .it.on {{ background:#132a55; color:#60a5fa; }}

/* cabeçalho */
.hero {{ position:relative; overflow:hidden; display:flex; justify-content:space-between; align-items:flex-start;
         padding:6px 4px 10px; min-height:96px; }}
.hero .tt {{ display:flex; gap:18px; align-items:flex-start; z-index:2; }}
.hero h1 {{ font-size:2rem; font-weight:800; color:#fff; margin:0; padding:0; line-height:1.15; }}
.hero p {{ color:#cbd5e1; margin:4px 0 0; font-size:.95rem; max-width:470px; }}
.hero .bg {{ position:absolute; right:150px; top:-30px; opacity:.55; z-index:1; transform:rotate(-12deg); }}
.upd {{ z-index:2; display:flex; gap:12px; align-items:center; background:#0b162bcc; border:1px solid #1c2c4a;
        border-radius:10px; padding:12px 16px; color:#cbd5e1; font-size:.8rem; }}
.upd b {{ display:block; color:#fff; font-size:.88rem; font-weight:600; }}

/* KPIs */
.kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; }}
.kpi {{ border-radius:10px; padding:16px 16px; display:flex; gap:14px; align-items:center;
        background:linear-gradient(180deg,#0c1830,#09132a); border:1.5px solid; }}
.kpi .ic {{ width:50px; height:50px; min-width:50px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}
.kpi .lb {{ font-size:.85rem; color:#e2e8f0; font-weight:600; }}
.kpi .vl {{ font-size:1.75rem; color:#fff; font-weight:700; line-height:1.25; }}
.kpi .sb {{ font-size:.78rem; color:#cbd5e1; }}

/* cards */
[class*="st-key-card"] {{ background:linear-gradient(180deg,#0b1730,#081227); border:1px solid #1a2a48;
                         border-radius:12px; padding:16px 18px 10px; }}
.ch {{ display:flex; gap:14px; align-items:flex-start; }}
.ch .h3 {{ font-size:1.12rem !important; font-weight:700; color:#fff; margin:0; padding:0 !important; }}
.ch span {{ font-size:.8rem; color:#cbd5e1; }}

/* barras */
.bars {{ display:flex; flex-direction:column; gap:6px; margin-top:8px; }}
.bar {{ display:grid; grid-template-columns:34px 1fr 64px; align-items:center; gap:10px; font-size:.82rem; color:#e2e8f0; }}
.bar .tr {{ height:15px; }}
.bar .fl {{ height:100%; border-radius:2px; }}
.bar .v {{ text-align:right; font-weight:600; }}

/* legenda do mapa */
.lg {{ display:flex; flex-direction:column; gap:15px; margin-top:28px; font-size:.78rem; color:#cbd5e1; }}
.lg div {{ white-space:nowrap; display:flex; align-items:center; gap:8px; }}
.lg i {{ flex:none; width:13px; height:13px; border-radius:50%; display:inline-block; }}
.lg b {{ margin-left:auto; color:#fff; font-weight:600; }}

/* insights */
.ins {{ display:flex; gap:16px; align-items:center; padding:16px 2px; border-bottom:1px solid #1a2a48; font-size:.8rem; color:#e2e8f0; }}
.ins:last-child {{ border-bottom:none; }}
.ins .ic {{ width:46px; height:46px; min-width:46px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}

.foot {{ display:flex; justify-content:space-between; align-items:center; color:#94a3b8; font-size:.75rem;
         font-style:italic; padding:4px 4px 0; }}
.foot .r {{ letter-spacing:.12em; font-style:normal; font-size:.7rem; color:#7c8db0; text-transform:uppercase; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- Trilho lateral
st.markdown(f"""
<div class="rail">
  <div class="it on">{icon("home", size=22)}</div>
  <div class="it">{icon("chart", size=20)}</div>
  <div class="it">{icon("map", size=20)}</div>
  <div class="it">{icon("doc", size=20)}</div>
  <div class="it">{icon("gear", size=20)}</div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- Cabeçalho
st.markdown(f"""
<div class="hero">
  <div class="tt">
    <div style="margin-top:2px">{icon("fuel", "#22c55e", 52, 2)}</div>
    <div><h1>Preço da Gasolina no Brasil</h1>
    <p>Acompanhe a evolução, compare entre estados e entenda as diferenças de preço no país.</p></div>
  </div>
  <div class="upd">{icon("calendar", "#e2e8f0", 22)}<div>Dados da semana de<b>{data_br(SEMANA)}</b></div></div>
</div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- KPIs
def kpi(cor, ic, label, valor, sub):
    return (f'<div class="kpi" style="border-color:{cor}"><div class="ic" style="background:{cor}33">'
            f'{icon(ic, cor, 24)}</div><div><div class="lb">{label}</div><div class="vl">{valor}</div>'
            f'<div class="sb">{sub}</div></div></div>')


def variacao(pct):
    # queda de preço é boa notícia (verde); alta, laranja
    cor, seta = (GREEN, "↓") if pct < 0 else (ORANGE, "↑")
    return f'<span style="color:{cor};font-weight:700">{seta}&nbsp; {"+" if pct > 0 else ""}{br(pct, 1)}%</span>'


st.markdown('<div class="kpis">' + "".join([
    kpi(BLUE, "fuel", "Preço Médio Nacional", f"R$ {br(BR.preco_atual)}", f"{variacao(VAR_MES)} vs. mês anterior"),
    kpi(ORANGE, "bars", "Maior Preço", f"R$ {br(MAIOR.preco_atual)}", ROTULO(MAIOR)),
    kpi(GREEN, "down", "Menor Preço", f"R$ {br(MENOR.preco_atual)}", ROTULO(MENOR)),
    kpi(PURPLE, "trend", "Variação em 12 meses", f"{br(BR.variacao_12m_pct)}%",
        f"{variacao(BR.variacao_12m_pct)} vs. mesma semana de {SEMANA.year - 1}"),
    kpi(CYAN, "pin", "Estados Pesquisados", str(UFS.preco_atual.notna().sum()),
        f"{int(BR.n_coletas_atual):,} coletas na semana".replace(",", ".")),
]) + "</div>", unsafe_allow_html=True)


def cabecalho(ic, cor, titulo, sub, extra=""):
    st.markdown(f'<div class="ch"><div>{icon(ic, cor, 26)}</div><div style="flex:1"><div class="h3">{titulo}</div>'
                f'<span>{sub}</span></div>{extra}</div>', unsafe_allow_html=True)


PLOT_CFG = {"displayModeBar": False}
BASE_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                   font=dict(family="Inter, sans-serif", color=MUTED, size=11),
                   hoverlabel=dict(bgcolor="#0b1730", bordercolor="#1a2a48", font_color="#e2e8f0"))

esq, dir_ = st.columns([3.05, 1])

# ---------------------------------------------------------------- Evolução
with esq:
    with st.container(key="card_linha"):
        cabecalho("trend", BLUE, "Evolução do preço da gasolina",
                  "Média nacional e estados com maior e menor preço atual (R$ / litro, média semanal)")
        series = [("BR", "Brasil (média)", BLUE), (MAIOR.codigo, ROTULO(MAIOR), ORANGE),
                  (MENOR.codigo, ROTULO(MENOR), GREEN)]
        # grade semanal completa: semanas sem dado viram NaN e a linha fica interrompida
        semanas = pd.date_range(SEMANAL.semana.min(), SEMANA, freq="W-MON")
        df = (SEMANAL[SEMANAL.codigo.isin([c for c, _, _ in series]) & (SEMANAL.nivel != "regiao")]
              .pivot(index="semana", columns="codigo", values="preco_medio").reindex(semanas))
        fig = go.Figure()
        for cod, nome, cor in series:
            fig.add_trace(go.Scatter(x=df.index, y=df[cod], name=nome, mode="lines", connectgaps=False,
                                     line=dict(color=cor, width=2),
                                     hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:.2f}<extra>" + nome + "</extra>"))
        fim = df.index[-1]
        for cod, nome, cor in series:
            y = df[cod].iloc[-1]
            fig.add_trace(go.Scatter(x=[fim], y=[y], mode="markers", marker=dict(color=cor, size=6),
                                     showlegend=False, hoverinfo="skip"))
            fig.add_annotation(x=fim, y=y, text=f"<b>R$ {br(y)}</b>", showarrow=False, xanchor="left", xshift=10,
                               font=dict(color=cor, size=12))
        y_min, y_max = float(df.min().min()), float(df.max().max())
        topo = y_max + 0.35
        # lacuna da ANP: 1º semestre de 2022 não foi publicado
        fig.add_vrect(x0="2022-01-01", x1="2022-07-01", fillcolor="#1e293b", opacity=0.5, line_width=0)
        fig.add_annotation(x="2022-01-08", y=topo, text="Sem dados<br>publicados (ANP)", showarrow=False,
                           xanchor="left", yanchor="top", align="left", font=dict(color="#94a3b8", size=10))
        fig.add_vline(x=pd.Timestamp("2023-05-16").timestamp() * 1000, line=dict(color="#475569", width=1, dash="dash"))
        fig.add_annotation(x="2023-05-16", y=topo, text="Petrobras abandona<br>o PPI (mai/2023)", showarrow=False,
                           xanchor="left", yanchor="top", xshift=8, align="left", font=dict(color="#cbd5e1", size=10))
        ticks = np.arange(np.floor(y_min * 2) / 2, topo + 0.01, 0.5)
        fig.update_layout(**BASE_LAYOUT, height=290, margin=dict(l=0, r=70, t=10, b=0), hovermode="x unified",
                          legend=dict(orientation="h", x=1, xanchor="right", y=1.17, font=dict(color="#cbd5e1", size=10),
                                      traceorder="normal", itemwidth=30),
                          xaxis=dict(showgrid=False, linecolor=GRID, tickformat="%Y", dtick="M12",
                                     range=[df.index[0] - pd.Timedelta(days=45), fim + pd.Timedelta(days=10)]),
                          yaxis=dict(range=[y_min - 0.1, topo + 0.05], tickvals=ticks,
                                     ticktext=[f"R$ {br(v, 1)}" for v in ticks], gridcolor=GRID, zeroline=False))
        st.plotly_chart(fig, width="stretch", config=PLOT_CFG)

    c1, c2 = st.columns([1, 1.17])

    # ------------------------------------------------------------ Ranking
    with c1:
        with st.container(key="card_barras"):
            cabecalho("trophy", "#60a5fa", "Preço médio por estado",
                      f"R$ / litro · semana de {SEMANA:%d/%m/%Y} · 6 mais caros e 4 mais baratos")
            ranking = list(UFS.head(6).itertuples()) + [None] + list(UFS.tail(4).itertuples())
            linhas = []
            for r in ranking:
                if r is None:
                    linhas.append('<div class="bar"><span>...</span><span></span><span></span></div>')
                    continue
                caro = r.Index < 6
                grad = ("linear-gradient(90deg,#ef4444,#f97316 40%,#fb923c)" if caro
                        else "linear-gradient(90deg,#1e40af,#2563eb 50%,#3b82f6)")
                largura = (r.preco_atual - 2.0) / (P_MAX - 2.0) * 100
                cor_v = "#fb923c" if r.Index == 0 else "#e2e8f0"
                linhas.append(f'<div class="bar"><span>{r.codigo}</span><div class="tr"><div class="fl" '
                              f'style="width:{largura:.1f}%;background:{grad}"></div></div>'
                              f'<span class="v" style="color:{cor_v}">R$ {br(r.preco_atual)}</span></div>')
            st.markdown('<div class="bars">' + "".join(linhas) + "</div><div style='height:10px'></div>",
                        unsafe_allow_html=True)

    # ------------------------------------------------------------ Faixa de preço (dumbbell)
    with c2:
        with st.container(key="card_faixa"):
            leg = (f'<div style="display:flex;gap:16px;font-size:.72rem;color:#cbd5e1;padding-top:4px">'
                   f'<span><span style="color:{BLUE}">●</span> Mínimo</span>'
                   f'<span><span style="color:{TEAL}">●</span> Média</span>'
                   f'<span><span style="color:{ORANGE}">●</span> Máximo</span></div>')
            cabecalho("sliders", "#60a5fa", "Faixa de preço por estado",
                      f"Médias semanais desde {UFS.primeira_semana.min():%Y} · valor à direita = atual", leg)
            f = pd.concat([UFS.head(5), UFS.tail(5)]).iloc[::-1].copy()
            f["estado"] = [ROTULO(r) for r in f.itertuples()]
            fig = go.Figure()
            for _, r in f.iterrows():
                fig.add_trace(go.Scatter(x=[r.minimo_semanal, r.maximo_semanal], y=[r.estado] * 2, mode="lines",
                                         line=dict(color="#3b82f6", width=1.2), showlegend=False, hoverinfo="skip"))
            for col, cor, nome in [("minimo_semanal", BLUE, "Mínimo"), ("media_periodo", TEAL, "Média"),
                                   ("maximo_semanal", ORANGE, "Máximo")]:
                fig.add_trace(go.Scatter(x=f[col], y=f["estado"], mode="markers", name=nome,
                                         marker=dict(color=cor, size=8),
                                         hovertemplate="%{y}<br>" + nome + ": R$ %{x:.2f}<extra></extra>"))
            for _, r in f.iterrows():
                fig.add_annotation(x=1.0, xref="paper", y=r.estado, text=br(r.preco_atual), showarrow=False,
                                   xanchor="left", xshift=14, font=dict(color="#e2e8f0", size=12))
            x0, x1 = np.floor(f.minimo_semanal.min() * 2) / 2, np.ceil(f.maximo_semanal.max() * 2) / 2
            xt = np.arange(np.ceil(x0), x1 + 0.01, 1.0)
            fig.update_layout(**BASE_LAYOUT, height=275, margin=dict(l=150, r=45, t=8, b=0), showlegend=False,
                              xaxis=dict(range=[x0 - 0.1, x1 + 0.05], tickvals=xt, ticktext=[br(v, 1) for v in xt],
                                         gridcolor=GRID, zeroline=False, showline=False),
                              yaxis=dict(showgrid=False, tickfont=dict(color="#e2e8f0", size=11), ticksuffix="  ", automargin=False,
                                         showline=True, linecolor="#334155"))
            st.plotly_chart(fig, width="stretch", config=PLOT_CFG)

# ---------------------------------------------------------------- Mapa por região
with dir_:
    with st.container(key="card_mapa"):
        cabecalho("map", CYAN, "Preço médio por região", f"(R$ / litro · semana de {SEMANA:%d/%m})")
        m1, m2 = st.columns([1.25, 1], vertical_alignment="center")
        with m1:
            nome_reg = dict(zip(REG.codigo, REG.nome))
            dfm = UFS.assign(regiao_nome=UFS.regiao.map(nome_reg))
            fig = px.choropleth(dfm, geojson=geojson_brasil(), locations="codigo", featureidkey="properties.sigla",
                                color="preco_atual", color_continuous_scale=ESCALA, range_color=[P_MIN, P_MAX],
                                custom_data=["regiao_nome", "preco_atual"])
            fig.update_traces(marker_line_color="#0b1730", marker_line_width=0.8,
                              hovertemplate="<b>%{location}</b> · %{customdata[0]}<br>R$ %{customdata[1]:.2f}<extra></extra>")
            fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                            lonaxis_range=[-74.5, -34], lataxis_range=[-34, 5.5])
            fig.update_layout(**BASE_LAYOUT, height=210, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                              coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch", config=PLOT_CFG)
        with m2:
            st.markdown('<div class="lg">' + "".join(
                f'<div><i style="background:{cor_preco(r.preco_atual)}"></i>{r.nome}<b>R$ {br(r.preco_atual)}</b></div>'
                for r in REG.itertuples()) + "</div>", unsafe_allow_html=True)

    # ------------------------------------------------------------ Insights (calculados a partir do gold)
    with st.container(key="card_insights"):
        def insight(ic, cor, txt):
            return (f'<div class="ins"><div class="ic" style="background:{cor}2e">{icon(ic, cor, 22)}</div>'
                    f'<div>{txt}</div></div>')

        alta = UFS.loc[UFS.variacao_12m_pct.idxmax()]
        reg_cara = REG.iloc[0]
        sentido = "subiu" if VAR_MES > 0 else "caiu"
        st.markdown(
            f'<div class="ch" style="align-items:center;padding:4px 0 2px">{icon("bulb", "#e2e8f0", 26)}'
            f'<div class="h3">Principais insights</div></div>'
            + insight("trend", ORANGE, f"<b>{ROTULO(MAIOR)}</b> tem o <b>maior preço médio</b> do país "
                                       f"(R$ {br(MAIOR.preco_atual)}).")
            + insight("down", GREEN, f"<b>{ROTULO(MENOR)}</b> tem o menor preço médio (R$ {br(MENOR.preco_atual)}), "
                                     f"R$ {br(MAIOR.preco_atual - MENOR.preco_atual)} abaixo do mais caro.")
            + insight("bar_up", BLUE, f"O preço médio nacional {sentido} {br(abs(VAR_MES), 1)}% em relação a "
                                      f"4 semanas antes. A região <b>{reg_cara.nome}</b> é a mais cara.")
            + insight("trend", PURPLE, f"Maior alta em 12 meses: <b>{ROTULO(alta)}</b> "
                                       f"(+{br(alta.variacao_12m_pct, 1)}%)."),
            unsafe_allow_html=True)

# ---------------------------------------------------------------- Rodapé
st.markdown(f"""
<div class="foot">
  <div style="display:flex;gap:14px;align-items:center">{icon("fuel", "#60a5fa", 22)}
  Fonte: ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis) &nbsp;|&nbsp; Gasolina comum, médias semanais das coletas em postos.</div>
  <div class="r">Combustível mais caro, impacta o seu dia a dia.</div>
</div>""", unsafe_allow_html=True)
