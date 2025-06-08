from dash import Input, Output, ctx, no_update
from datetime import datetime

def register_callbacks(dash_app):
    @dash_app.callback(
        Output("date-range", "start_date"),
        Output("date-range", "end_date"),
        Output("url", "pathname"),
        Input("btn-this-year", "n_clicks"),
        Input("btn-back-home", "n_clicks"),
        prevent_initial_call=True
    )
    def update_date_and_redirect(n_this_year, n_back_home):
        triggered_id = ctx.triggered_id

        if triggered_id == "btn-this-year":
            return "2025-03-01", datetime.now().strftime("%Y-%m-%d"), no_update
        elif triggered_id == "btn-back-home":
            return no_update, no_update, "/"
        return no_update, no_update, no_update
