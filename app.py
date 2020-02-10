import os
import logging

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
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

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
        ], style={'position': 'relative', 'zIndex': 999}),
    dbc.Row([
        dbc.Col(lg=1),
        dbc.Col([
            dcc.Loading([
                dcc.Graph(id='chart',
                          figure=go.Figure({'layout':
                                {'paper_bgcolor': '#eeeeee',
                                 'plot_bgcolor': '#eeeeee',
                                  'template': 'none'}},
                           {'config': {'displayModeBar': False}}),
                          config={'displayModeBar': False})
            ])
        ], lg=10)
    ]),
    dbc.Row([
        html.Br(),
        dbc.Col(lg=1),
        dbc.Col([
            DataTable(id='table',
                      style_header={'textAlign': 'center'},
                      style_cell={'font-family': 'Source Sans Pro',
                                  'minWidth': 100,
                                  'textAlign': 'left'
                                  },
                      style_cell_conditional=[
                          {'if': {'column_id': 'Tweet Volume'},
                           'textAlign': 'right'},
                          {'if': {'column_id': 'Local Rank'},
                           'textAlign': 'right'},
                          {'if': {'column_id': 'Topic'},
                           'textAlign': 'center'}
                      ],
                      columns=[{'name': i, 'id': i,
                                'type': 'numeric' if i == 'Tweet Volume' else None,
                                'format': Format(group=',')
                                if i == 'Tweet Volume' else None}
                               for i in TABLE_COLS],
                      sort_action='native',
                      export_headers='names',
                      export_format='csv',
                      page_action='none',
                      style_table={'overflowX': 'scroll'},
                      fixed_rows={'headers': True, 'data': 0},
                      data=pd.DataFrame({
                          k: ['' for i in range(10)] for k in TABLE_COLS
                      }).to_dict('rows'))
        ], lg=10),
        ], style={'font-family': 'Source Sans Pro'}),
] + [html.Br() for i in range(8)],
    style={'background-color': '#eeeeee', 'font-family': 'Source Sans Pro',
           'zIndex': 999},
    fluid=True)


@app.callback([Output('table', 'data'),
               Output('url', 'search'),
               Output('chart', 'figure')],
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
        n_countries = df['country'].nunique()
        countries = df['country'].unique()
        fig = make_subplots(rows=n_countries, cols=1,
                            subplot_titles=['Worldwide' if not c else c
                                            for c in countries],
                            specs=[[{'type': 'treemap'}]
                                   for i in range(n_countries)],
                            vertical_spacing=0.05)
        for i, c in enumerate(countries):
            sub_fig_df = df[df['country'] == c]
            sub_fig = px.treemap(sub_fig_df,
                                 path=['country', 'location', 'name'],
                                 values='tweet_volume')
            sub_fig.layout.margin = {'b': 5, 't': 5}
            sub_fig.data[0]['hovertemplate'] = '<b>%{label}</b><br>Tweet volume: %{value}'
            last_line = '' if c == '' else '<br>%{percentRoot} of %{root}'
            sub_fig.data[0]['texttemplate'] = '<b>%{label}</b><br><br>Tweet volume: %{value}<br>%{percentParent} of %{parent}' + last_line
            fig.add_trace(sub_fig.to_dict()['data'][0], row=i+1, col=1)
        fig.layout.height = 400 * n_countries
        fig.layout.template = 'none'
        fig.layout.margin = {'t': 40, 'b': 40}
        fig.layout.paper_bgcolor = '#eeeeee'
        fig.layout.plot_bgcolor = '#eeeeee'

        final_df = df.drop(['promoted_content', 'woeid', 'parentid'], axis=1)
        final_df = final_df.rename(columns={'name': 'Topic'})
        final_df.columns = [x.title() for x in final_df.columns.str.replace('_', ' ')]
        url_search = '?q=' + '+'.join(log_loc)
        return final_df.to_dict('rows'), url_search, fig.to_dict()
    except Exception as e:
        return pd.DataFrame({'Name': ['Too many requests please '
                                      'try again in 15 minutes.']},
                            columns=df.columns).to_dict('rows')


if __name__ == '__main__':
    app.run_server()
