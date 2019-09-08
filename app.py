import os
import logging

from six.moves.urllib.parse import quote
import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_table import DataTable
from dash_table.FormatTemplate import Format
import pandas as pd
import advertools as adv

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s==%(funcName)s==%(message)s')

app_key = os.environ['app_key']
app_secret = os.environ['app_secret']
oauth_token = os.environ['oauth_token']
oauth_token_secret = os.environ['oauth_token_secret']

auth_params = {'app_key': app_key,
               'app_secret': app_secret,
               'oauth_token': oauth_token,
               'oauth_token_secret': oauth_token_secret,}
adv.twitter.set_auth_params(**auth_params)

trend_locs = adv.twitter.get_available_trends() 
locations = trend_locs['name'] + ', ' + trend_locs['country']

TABLE_COLS = ['Topic', 'Location', 'Tweet Volume',
              'Local Rank', 'Country', 'Time', 'Place Type']

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server


app.layout = dbc.Container([
    html.Br(),
    dcc.Location(id='url', refresh=False),
    dbc.Row([
        dbc.Col(lg=1),
        dbc.Col([
                dcc.Dropdown(id='locations',
                             placeholder='Select location(s)',
                             multi=True,
                             options=[{'label': loc, 'value': i}
                                      for i, loc in enumerate(locations)]),
            ], lg=5),
        dbc.Col([
            dbc.Button(id='button', children='Submit',
                       n_clicks=0, color='dark'),
        ]),
        dbc.Col([
            # html.Br(),
            html.A('Download Table',
            id='download_link',
            download="rawdata.csv",
            href="",
            target="_blank",
            n_clicks=0),
            ], lg=2, align='left')
        ], style={'position': 'relative', 'zIndex': 999}),
    dbc.Container([
        html.Br(),
        dcc.Loading([
            DataTable(id='table',
                      style_cell={'font-family': 'Source Sans Pro', 'minWidth': 100},
                      columns=[{'name': i, 'id': i,
                                'type': 'numeric' if i == 'Tweet Volume' else None,
                                'format': Format(group=',')
                                if i == 'Tweet Volume' else None}
                               for i in TABLE_COLS],
                      sort_action='native',
                      fixed_rows={'headers': True, 'data': 0},
                      data=pd.DataFrame({
                          k: ['' for i in range(10)] for k in TABLE_COLS
                      }).to_dict('rows'),
                      ),
        ]),
        ], style={'width': '95%', 'margin-left': '2.5%',
                  'background-color': '#eeeeee',
                  'font-family': 'Source Sans Pro'},
    fluid=True),
    html.Br(), html.Br(), html.Br(), html.Br(), html.Br()
], style={'background-color': '#eeeeee', 'font-family': 'Source Sans Pro'},
    fluid=True)


@app.callback([Output('table', 'data'),
               Output('url', 'search')],
              [Input('button', 'n_clicks')],
              [State('locations', 'value')])
def set_table_data(n_clicks, locations):
    if not n_clicks:
        raise PreventUpdate
    log_loc = trend_locs['name'][locations]
    logging.info(msg=list(log_loc))
    try:
        woeid = trend_locs['woeid'][locations]
        df = adv.twitter.get_place_trends(woeid)

        final_df = df.drop(['promoted_content', 'woeid', 'parentid'], axis=1)
        final_df = final_df.rename(columns={'name': 'Topic'})
        final_df.columns = [x.title() for x in final_df.columns.str.replace('_', ' ')]
        url_search = '?q=' + '+'.join(log_loc)
        return final_df.to_dict('rows'), url_search
    except Exception as e:
        return pd.DataFrame({'Name': ['Too many requests please '
                                      'try again in 15 minutes.']},
                            columns=df.columns).to_dict('rows')


@app.callback(Output('download_link', 'href'),
              [Input('table', 'data')])
def download_df(data_df):
    df = pd.DataFrame.from_dict(data_df, 'columns')
    csv_string = df.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + quote(csv_string)
    return csv_string


if __name__ == '__main__':
    app.run_server(debug=True)
