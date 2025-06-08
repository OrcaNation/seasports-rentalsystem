from dash import Dash
import dash_bootstrap_components as dbc

def init_dash(server):
    dash_app = Dash(
        __name__,
        server=server,  # esse `server` vem do `init_dash(app)`
        url_base_pathname="/dashboard/",
        external_stylesheets=[

            dbc.themes.BOOTSTRAP,
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
            "https://fonts.googleapis.com/css2?family=Roboto&display=swap",
            "https://fonts.googleapis.com/css2?family=Kanit:wght@900&display=swap",
            "/static/css/styles.css",
        ]
    )

    from dash_app.layout import layout
    from dash_app.callbacks import register_callbacks

    dash_app.layout = layout
    register_callbacks(dash_app)

    return dash_app