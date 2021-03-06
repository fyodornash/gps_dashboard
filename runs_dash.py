import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from textwrap import dedent
from garmin_tools import *
from time import time
from datetime import datetime
import json

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client.garmin

start_time = time()

def df_run(run):
    try:
        return pd.DataFrame(run['df'])
    except ValueError:
        df = pd.DataFrame(json.loads(run['df'].replace("'",'"')))
        df.Time = pd.to_datetime(df.Time)
        return df
runs = [run for run in db.runsy.find()]
runs_date = {str(run['time']).split()[0]:df_run(run) for run in runs}
speed_zones_date = {str(run['time']).split()[0]:run['speed_zones'] for run in runs}
hr_zones_date = {str(run['time']).split()[0]:run.get('hr_zones') for run in runs}
runs_dict= {str(run['time']).split()[0]:run for run in runs}
TSSes = [[tss,date] for [tss,date,c,d] in get_training_summary(db)]
colors = ['#222222','#be3030','ff7100','7b3c3c','db5f29']
dates = sorted(runs_date.keys())

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}



app = dash.Dash()
app.css.append_css({'external_url':'https://codepen.io/chriddyp/pen/dZVMbK.css'})
app.config.update({
        # as the proxy server will remove the prefi
        'routes_pathname_prefix': '/dashboard/',

         # the front-end will prefix this string to the requests
        # that are made to the proxy server
        'requests_pathname_prefix': '/dashboard/'
})
server = app.server
app.layout = html.Div([
    html.Div(dcc.Markdown(id = 'stress-md',className="twelve columns"),style={"text-align": "center"}),
    html.Div(dcc.Graph(id='graph-with-dropdown'),className="six columns"),
    html.Div(dcc.Graph(
        id='graph2-with-dropdown'),
        className="six columns"),
    html.Div(children='Selected Run:',style={"text-align": "center",'fontSize':16},className="one column"),
    html.Div(dcc.Dropdown(
        id='year-dropdown',
        value=dates[-1],
        options=[{'label':d,'value':d} for d in dates]
    ), className="two columns"),
    html.Div([
        html.Div(dcc.Graph(id='graph4'),
            className='nine columns'),
        html.Div([
            dcc.Markdown(dedent("""
                **Selected Run**
            """)),
            html.Pre(id='click-data', style=styles['pre']),
        ], className='three columns')], className= 'twelve columns')
    ,
    html.Div(dcc.Graph(id='graph3'),
        className='twelve columns')

])

@app.callback(
    dash.dependencies.Output('year-dropdown', 'options'),
    [dash.dependencies.Input('year-dropdown', 'value')])
def update_dropdown(_):
    return [{'label':d,'value':d} for d in dates]


@app.callback(
    dash.dependencies.Output('graph-with-dropdown', 'figure'),
    [dash.dependencies.Input('graph4', 'clickData')])
def update_figure(clickData):
    selected_date = clickData['points'][0]['text'].split('<br>')[2].split(' ')[0]
    global start_time
    delta_time = time()-start_time
    if delta_time>8000:
        print('updating data')
        start_time = time()
        global runs_date, runs, speed_zones_date, hr_zones_date, runs_dict, TSSes
        runs = [run for run in db.runsy.find()]
        runs_date = {str(run['time']).split()[0]:df_run(run) for run in runs}
        speed_zones_date = {str(run['time']).split()[0]:run['speed_zones'] for run in runs}
        hr_zones_date = {str(run['time']).split()[0]:run.get('hr_zones') for run in runs}
        runs_dict= {str(run['time']).split()[0]:run for run in runs}
        TSSes = [[tss,date] for [tss,date,c,d] in get_training_summary(db)]
    filtered_df = runs_date[selected_date]
    traces = []
    for i,color in zip(list(set([d for d in filtered_df.columns]) - set(['Time', 'time', 'Distance'])),colors):

        traces.append(go.Scatter(
            x=filtered_df['Distance'],
            y=filtered_df[i],
            name=i,
            line = dict(color = color)
        ))

    return {
        'data': traces,
        'layout': go.Layout(
            title = 'Run Details'
        )
    }


@app.callback(
    dash.dependencies.Output(component_id='stress-md', component_property='children'),
    [dash.dependencies.Input('graph4', 'clickData')])
def update_output_md(clickData):
    selected_date = clickData['points'][0]['text'].split('<br>')[2].split(' ')[0]
    if runs_dict[selected_date].get('TSS'):
        return dedent('''
# Stress Score : **{0:.2f}** ___________  Cardiac Drift : {1:.2f}
'''.format(runs_dict[selected_date].get('TSS'),runs_dict[selected_date].get('cardiac_drift')))
    else:
        return '# There is no heartrate data for this run'

@app.callback(
    dash.dependencies.Output('graph2-with-dropdown', 'figure'),
    [dash.dependencies.Input('graph4', 'clickData')])
def update_figure2(clickData):
    selected_date = clickData['points'][0]['text'].split('<br>')[2].split(' ')[0]
    filtered_speed = speed_zones_date[selected_date]
    filtered_hr = hr_zones_date[selected_date]

    traces = []
    zones = sorted(filtered_speed.keys())

    traces.append(go.Bar(
        x=zones,
        y=[filtered_speed[zone] for zone in zones],
        name='Pace Zones',
        text = zones_text_pace(),
        marker = dict(color = colors[0])
        ))
    if filtered_hr:
        traces.append(go.Bar(y =[filtered_hr[zone] for zone in zones],
            x = zones, name ='HR', text = zones_text_hr(),
            marker = dict(color = colors[1])))

    return {
        'data': traces,
        'layout': go.Layout(
            title = 'Pace and HR Zones',hovermode="closest",yaxis = {'title':'Minutes in Zone','hoverformat':'.2f'}
        )
    }

@app.callback(
    dash.dependencies.Output('graph3', 'figure'),
    [dash.dependencies.Input('year-dropdown', 'value')])
def update_figure3(selected_date):
    return plot_training_loads(TSSes,selected_date)


@app.callback(
    dash.dependencies.Output('click-data', 'children'),
    [dash.dependencies.Input('graph4', 'clickData')])
def display_click_data(clickData):
    return json.dumps(clickData['points'][0]['text'].split('<br>')[2].split(' ')[0], indent=2)


@app.callback(
    dash.dependencies.Output('graph4', 'figure'),
    [dash.dependencies.Input('year-dropdown', 'value')])
def update_figure3(selected_date):
    df = pd.DataFrame(get_training_summary(db))
    return heat_map_running(df)

if __name__ == '__main__':
    app.run_server()
