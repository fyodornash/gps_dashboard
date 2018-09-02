import pandas as pd

from textwrap import dedent
from garmin_tools import *
from time import time
import json

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

import config
from auth import auth

print('starting app.py')


start_time = time()
print('creating app')
app = dash.Dash(
    __name__,
)
auth(app)

server = app.server  # Expose the server variable for deployments


print('load the runs')

@mongo_decorator
def get_runs(db = None):
    return [run for run in db.runsy.find()]
print('loading runs')



runs, runs_date, speed_zones_date, hr_zones_date, runs_dict, dates = [], {}, {}, {}, {},[]
df = pd.DataFrame(get_training_summary())
df = add_weeks(df)
weeks = list(df.week.unique())
TSSes = [[tss, date] for [tss, date, c, d] in get_training_summary()]
dates = [d for t, d in TSSes]
colors = ['#222222', '#be3030', '#ff7100', '#7b3c3c', '#db5f29']

print('finished')
styles = {
    'pre': {
        'border': 'thin lightgrey solid'
    }
}

print('creating the app layout')
app.layout = html.Div([
    html.Div(dcc.Markdown(id = 'stress-md', className="twelve columns"), style={"text-align": "center"}),
    html.Div(dcc.Graph(id='graph-with-dropdown'),className="six columns"),
    html.Div(dcc.Graph(
        id='graph2-with-dropdown'),
        className="six columns"),
    html.Div([
        html.Div(dcc.Graph(id='graph4'),
            className='nine columns'),
        html.Div([
            dcc.Markdown(dedent("""
                **Selected Run**
            """)),
            dcc.Markdown(id='click-data'),
            dcc.Markdown(dedent("""

                **From:**
            """)),
            dcc.Dropdown(
                id='week-start-dropdown',
                value=len(weeks) - 4,
                options= [{'label':week,'value':n} for n,week in enumerate(weeks)]
            ),
            dcc.Markdown(dedent("""

                **To:**
            """)),
            dcc.Dropdown(
                id='week-end-dropdown',
                value=len(weeks) - 1,
                options=[{'label':week,'value':n} for n,week in enumerate(weeks)]
            )
        ], className='three columns')], className= 'twelve columns')
    ,
    html.Div(dcc.Graph(id='graph3'),
    className='twelve columns')

])


@app.callback(
    dash.dependencies.Output('week-end-dropdown', 'options'),
    [dash.dependencies.Input('week-end-dropdown', 'value')])
def update_dropdown(week):
    return [{'label':week,'value':n} for n,week in enumerate(weeks)]


@app.callback(
    dash.dependencies.Output('week-start-dropdown', 'options'),
    [dash.dependencies.Input('week-start-dropdown', 'value')])
def update_dropdown(week):
    return [{'label':week,'value':n} for n,week in enumerate(weeks)]


@app.callback(
    dash.dependencies.Output('graph-with-dropdown', 'figure'),
    [dash.dependencies.Input('graph4', 'clickData')])
def update_figure(clickData):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = '2018-07-10 11:36:43'
    filtered_df, _, _, _ = search_run(time=selected_date)
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
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = '2018-07-10 11:36:43'
    filtered_df, _, _, run = search_run(time=selected_date)
    if run.get('TSS'):
        return dedent('''
# Stress Score : **{0:.2f}** ___________  Cardiac Drift : {1:.2f}
'''.format(run.get('TSS'),run.get('cardiac_drift')))
    else:
        return '# There is no heartrate data for this run'

@app.callback(
    dash.dependencies.Output('graph2-with-dropdown', 'figure'),
    [dash.dependencies.Input('graph4', 'clickData')])
def update_figure2(clickData):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = '2018-07-10 11:36:43'
    filtered_df, filtered_speed, filtered_hr, _ = search_run(time=selected_date)

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
    [dash.dependencies.Input('graph4', 'clickData')])
def update_figure3(clickData):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = '2018-07-10 11:36:43'
    filtered_df, _, _, _ = search_run(time=selected_date)
    return plot_training_loads(TSSes,selected_date)


@app.callback(
    dash.dependencies.Output('click-data', 'children'),
    [dash.dependencies.Input('graph4', 'clickData')])
def display_click_data(clickData):
    return json.dumps(clickData['points'][0]['text'].split('<br>')[2].split(' ')[0], indent=2)


@app.callback(
    dash.dependencies.Output('graph4', 'figure'),
    [dash.dependencies.Input('week-start-dropdown', 'value'),dash.dependencies.Input('week-end-dropdown', 'value')])
def update_figure4(start, end):
    df = pd.DataFrame(get_training_summary())
    return heat_map_running(df, start, end)

app.css.append_css({'external_url':'https://codepen.io/chriddyp/pen/dZVMbK.css'})

if __name__ == '__main__':
    app.run_server(debug=True)
