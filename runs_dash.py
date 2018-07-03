import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from textwrap import dedent
from garmin_tools import plot_training_loads,zones_text_pace,zones_text_hr
from time import time

from pymongo import MongoClient,InsertOne,UpdateOne
client = MongoClient('localhost',27017) 
db = client.garmin

start_time = time()
runs = [run for run in db.runs.find()]
runs_date = {run['time'].isoformat().split('T')[0]:pd.DataFrame(run['df']) for run in runs}
speed_zones_date = {run['time'].isoformat().split('T')[0]:run['speed_zones'] for run in runs}
hr_zones_date = {run['time'].isoformat().split('T')[0]:run.get('hr_zones') for run in runs}
runs_dict= {run['time'].isoformat().split('T')[0]:run for run in runs}
TSSes = [[run.get('TSS'),run['time']] for run in runs if run.get('TSS')]

dates = sorted(runs_date.keys())

app = dash.Dash()

app.css.append_css({'external_url':'https://codepen.io/chriddyp/pen/dZVMbK.css'})

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
    [dash.dependencies.Input('year-dropdown', 'value')])
def update_figure(selected_date):
    global start_time
    delta_time = time()-start_time
    if delta_time>8000:
        print('updating data')
        start_time = time()
        global runs_date,runs,speed_zones_date,hr_zones_date,runs_dict,TSSes
        runs = [run for run in db.runs.find()]
        runs_date = {run['time'].isoformat().split('T')[0]:pd.DataFrame(run['df']) for run in runs}
        speed_zones_date = {run['time'].isoformat().split('T')[0]:run['speed_zones'] for run in runs}
        hr_zones_date = {run['time'].isoformat().split('T')[0]:run.get('hr_zones') for run in runs}
        runs_dict= {run['time'].isoformat().split('T')[0]:run for run in runs}
        TSSes = [[run.get('TSS'),run['time']] for run in runs if run.get('TSS')]
    filtered_df = runs_date[selected_date]
    traces = []
    for i in set([d for d in filtered_df.columns]) - set(['Time','time','Distance']):
        
        traces.append(go.Scatter(
            x=filtered_df['Distance'],
            y=filtered_df[i],
            name=i
        ))

    return {
        'data': traces,
        'layout': go.Layout(
            title = 'Run Details'
        )
    }


@app.callback(
    dash.dependencies.Output(component_id='stress-md', component_property='children'),
    [dash.dependencies.Input('year-dropdown', 'value')]
)
def update_output_md(selected_date):
    if runs_dict[selected_date].get('TSS'):
        return dedent('''
# Stress Score : **{0:.2f}** ___________  Cardiac Drift : {1:.2f}
'''.format(runs_dict[selected_date].get('TSS'),runs_dict[selected_date].get('cardiac_drift')))
    else:
        return '# There is no heartrate data for this run'

@app.callback(
    dash.dependencies.Output('graph2-with-dropdown', 'figure'),
    [dash.dependencies.Input('year-dropdown', 'value')])
def update_figure2(selected_date):
    filtered_speed = speed_zones_date[selected_date]
    filtered_hr = hr_zones_date[selected_date]

    traces = []
    zones = sorted(filtered_speed.keys())
    
    traces.append(go.Bar(
        x=zones,
        y=[filtered_speed[zone] for zone in zones],
        name='Pace Zones',
        text = zones_text_pace()
        ))
    if filtered_hr:
        traces.append(go.Bar(y =[filtered_hr[zone] for zone in zones],x = zones, name ='HR',text = zones_text_hr()))

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

if __name__ == '__main__':
    app.run_server()