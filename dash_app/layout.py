import plotly.express as px
import pandas as pd
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

# --------------------------
# Dados de exemplo
# --------------------------
df_line = pd.DataFrame({
    "Date": pd.date_range(start="2025-06-01", periods=7),
    "Revenue": [120, 300, 250, 400, 180, 220, 310]
})

df_bar = pd.DataFrame({
    "Weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "Rentals": [12, 18, 9, 20, 15, 30, 25]
})

df_pie = pd.DataFrame({
    "Equipment": ["Mask", "Life Jacket", "Fins"],
    "Count": [40, 70, 20]
})

df_table = pd.DataFrame({
    "Date": ["2025-06-01", "2025-06-02", "2025-06-03"],
    "Guest": ["Alice", "Bob", "Charlie"],
    "Item": ["Mask", "Life Jacket", "Fins"],
    "Duration (h)": [2, 3, 1.5],
    "Price": [20, 30, 15]
})
orca_colors = ["#1e1542", "#f47d72", "#fde8e4", "#f4c542", "#48c4c4"]
# --------------------------
# Gráficos e Tabela
# --------------------------
line_chart = px.line(df_line, x="Date", y="Revenue", title="Revenue Over Time", height=350, color_discrete_sequence=[orca_colors[1]])
bar_chart = px.bar(df_bar, x="Weekday", y="Rentals", title="Rentals per Weekday", color_discrete_sequence=orca_colors)
pie_chart = px.pie(df_pie, values="Count", names="Equipment", title="Equipment Usage Share",color_discrete_sequence=orca_colors)

data_table = dash_table.DataTable(
    columns=[{"name": col, "id": col} for col in df_table.columns],
    data=df_table.to_dict("records"),
    page_size=10,
    style_table={"overflowX": "auto"},
    style_cell={"textAlign": "left", "fontFamily": "Roboto", "padding": "6px"},
    style_header={"backgroundColor": "#1e1542", "color": "white", "fontWeight": "bold"}
)

# --------------------------
# Função para cards
# --------------------------
def card_top(label, icon, content):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.I(className=f"bi bi-{icon} me-2", style={"fontSize": "2rem", "color": "black"}),
                html.H5(label, className="card-title mb-0", style={"color": "black"})
            ], style={"display": "flex", "alignItems": "center", "gap": "0.5rem"}),
            html.H2(content, className="card-text mt-2", style={"color": "white"})
        ]),
        style={"background-color": "#f47d72"},
        className="mb-4 shadow-sm rounded-4 orca-card"
    )

# --------------------------
# Navbar fixa no topo
# --------------------------
navbar = html.Nav(
    className="navbar navbar-custom",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "right": 0,
        "zIndex": 999,
        "height": "60px",
        "backgroundColor": "#1e1542"
    },
    children=[
        dbc.Container([
            html.A([
                html.Img(src="/static/img/title_1.png", className="navbar-logo", alt="Logo"),
                html.H1("Reports", className="navbar-title mb-0", style={"color": "white"})
            ],
            href="/",
            className="d-flex align-items-center text-decoration-none")
        ])
    ]
)

# --------------------------
# Sidebar fixa à esquerda
# --------------------------
sidebar = html.Div(
    style={
        "position": "fixed",
        "top": "60px",  # abaixo da navbar
        "left": 0,
        "bottom": 0,
        "width": "250px",
        "padding": "2rem 1rem",
        "backgroundColor": "#fde8e4",  # orca-pink
        "color": "#1e1542",  # orca-blue
        "fontFamily": "Roboto"
    },
    children=[

        html.H2("Filters", className="mb-4", style={"fontFamily": "Kanit", "textTransform": "uppercase"}),

        html.Label("Date Range", style={"fontWeight": "bold"}),
        dcc.DatePickerRange(
            id="date-range",
            start_date_placeholder_text="Start",
            end_date_placeholder_text="End",
            display_format="DD MMM YYYY",
            style={"marginBottom": "20px"}
        ),

        html.Label("Equipment Type", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="equipment-dropdown",
            options=[],
            multi=True,
            placeholder="Select equipment"
        ),

        # Botões lado a lado com espaçamento
        html.Div([
            html.Button([
                html.I(className="bi bi-calendar3 me-2"),  # ícone de calendário
                "This Year"
            ], id="btn-this-year", className="btn btn-secondary", n_clicks=0, style={"flex": "1", "marginRight": "8px"}),

            html.Button([
                html.I(className="bi bi-arrow-left-circle me-2"),  # ícone de seta para trás
                "Back"
            ], id="btn-back-home", className="btn btn-primary", n_clicks=0, style={"flex": "1"})
        ], style={"display": "flex", "marginTop": "2rem"})
    ]
)

# --------------------------
# Cards e conteúdo visual
# --------------------------
card_group = html.Div(
    dbc.Row([
        dbc.Col(card_top("Total Revenue", "cash-coin", "RM 33"), md=3),
        dbc.Col(card_top("Total Rents", "box-seam", "133"), md=3),
        dbc.Col(card_top("Time no equipment", "clock", "33h"), md=3),
        dbc.Col(card_top("Most rented item", "life-preserver", "Mask"), md=3),
    ],
    className="g-2"),  # gap entre colunas e linhas
    className="mt-5"
)

dashboard_bottom = html.Div([
    dbc.Row([
        dbc.Col([
            html.H5("Detailed Rentals", className="mb-3"),
            data_table
        ], width=12)
    ]),
    dbc.Row([dbc.Col(dcc.Graph(figure=line_chart), width=12)]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=bar_chart), width=6),
        dbc.Col(dcc.Graph(figure=pie_chart), width=6)
    ])
], className="mt-4")

# --------------------------
# Layout principal
# --------------------------
layout = html.Div([
dcc.Location(id='url', refresh=False),
    navbar,
    sidebar,
    html.Div([
        html.Div(card_group),
        dashboard_bottom
    ], className="p-4", style={
        "marginLeft": "250px",  # espaço para o sidebar
        "paddingTop": "80px",   # espaço para a navbar
        "minHeight": "100vh",
        "backgroundColor": "#f9f9f9"
    })
])
