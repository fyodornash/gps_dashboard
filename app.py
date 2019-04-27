import pandas as pd

from textwrap import dedent
from garmin_tools import *
from time import time
import json
from flask_caching import Cache

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

from accounts import get_users
from auth import auth

print('starting app.py')

start_time = time()
print('creating app')
app = dash.Dash(
    __name__,
)
auth(app)
print('routes: {}, requests: {}, base_url: {}'.format(
    app.config.get('routes_pathname_prefix'),
    app.config.get('requests_pathname_prefix'),
    app.config.get('url_base_pathname')))
server = app.server  # Expose the server variable for deployments

app.title = 'Training Log'

cache = Cache(app.server, config={
    # try 'filesystem' if you don't want to setup redis
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL', '')
})
cache.clear()
timeout = 86400

@cache.memoize(timeout=timeout*30)
def cached_training_summary(*args, **kwargs):
    return get_training_summary(*args, **kwargs)

colors = ['#222222', '#be3030', '#ff7100', '#7b3c3c', '#db5f29']

print('finished')
styles = {
    'pre': {
        'border': 'thin lightgrey solid'
    }
}




print('creating the app layout')
app.layout = html.Div([
    html.Div([
        dcc.Dropdown(id='user-dropdown', value='michael', className='two columns'),
        dcc.Markdown(id='stress-md', className="ten columns")], style={"text-align": "center"}),
    html.Div([
        html.Div(
            dcc.Graph(
                id='graph-with-dropdown'
            ), className="six columns"),
        html.Div(
            dcc.Graph(
                id='graph2-with-dropdown'
            ),className="six columns")]),
    html.Div([
        html.Div(
            dcc.Graph(id='graph4'),
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
            ),
            dcc.Markdown(dedent("""

                **To:**
            """)),
            dcc.Dropdown(
                id='week-end-dropdown',
            )
        ], className='three columns')], className='twelve columns')
    ,
    html.Div(dcc.Graph(id='graph3'),
             className='twelve columns')

])

# states to use
_user = State('user-dropdown', 'value')

@app.callback(
    Output('user-dropdown', 'options'),
    [Input('user-dropdown', 'id')])
def set_users(_):
    return [{'label': user['user_id'], 'value': user['user_id']} for user in get_users()]


@app.callback(
    Output('week-end-dropdown', 'value'),
    [Input('week-end-dropdown', 'id')],
    [_user])
def set_wed_value(_, user):
    df = pd.DataFrame(cached_training_summary(user_id=user))
    df = add_weeks(df)
    weeks = list(df.week.unique())
    return len(weeks) - 1


@app.callback(
    Output('week-start-dropdown', 'value'),
    [Input('week-start-dropdown', 'id')],
    [_user])
def set_wes_value(_, user):
    df = pd.DataFrame(cached_training_summary(user_id=user))
    df = add_weeks(df)
    weeks = list(df.week.unique())
    return len(weeks) - 4


@app.callback(
    Output('week-end-dropdown', 'options'),
    [Input('week-end-dropdown', 'value')],
    [_user])
def update_dropdown(week, user):
    df = pd.DataFrame(cached_training_summary(user_id=user))
    df = add_weeks(df)
    weeks = sorted(list(df.week.unique()))
    return [{'label': week, 'value': n} for n, week in enumerate(weeks)]


@app.callback(
    Output('week-start-dropdown', 'options'),
    [Input('week-start-dropdown', 'value')],
    [_user])
def update_dropdown(week, user):
    df = pd.DataFrame(cached_training_summary(user_id=user))
    df = add_weeks(df)
    weeks = sorted(list(df.week.unique()))
    return [{'label': week, 'value': n} for n, week in enumerate(weeks)]


@app.callback(
    Output('graph-with-dropdown', 'figure'),
    [Input('graph4', 'clickData')],
    [_user])
@cache.memoize(timeout=timeout*30)
def update_figure(clickData, user):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = str(cached_training_summary(user_id=user)[-1]['time'])
    filtered_df, _, _, _ = search_run(user_id=user, time=selected_date)
    traces = []
    for i, color in zip(list(set([d for d in filtered_df.columns]) - set(['Time', 'time', 'Distance'])), colors):
        traces.append(go.Scatter(
            x=filtered_df['Distance'],
            y=filtered_df[i],
            name=i,
            line=dict(color=color)
        ))
    intervals = get_intervals(filtered_df)
    if len(intervals) > 0:
        for a, b in intervals:
            ave_speed = (filtered_df.iloc[b].Distance - filtered_df.iloc[a].Distance) / (filtered_df.iloc[b].time - filtered_df.iloc[a].time) * 3.6
            minutes = 60 / ave_speed
            seconds = 60 * (minutes % 1)
            traces.append(go.Scatter(
                x=[filtered_df.Distance[a]],
                y=[ave_speed],
                text='{}:{:.0f}<br>min/km'.format(int(minutes), seconds),
                mode='text',
                textposition=['top left'],
                showlegend=False,
            ))
            traces.append(go.Scatter(
                x=[filtered_df.Distance[a], filtered_df.Distance[b]],
                y=[ave_speed, ave_speed],
                hoverinfo='skip',
                mode='lines',
                line=dict(color='black', dash='dot'),
                showlegend=False
            ))

    return go.Figure({
        'data': traces,
        'layout': go.Layout(
            title='Run Details'
        )
    }).to_dict()


@app.callback(
    Output(component_id='stress-md', component_property='children'),
    [Input('graph4', 'clickData')],
    [_user])
def update_output_md(clickData, user):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = str(cached_training_summary(user_id=user)[-1]['time'])
    filtered_df, _, _, run = search_run(user_id=user, time=selected_date)
    if run.get('TSS'):
        return dedent('''
# Stress Score : **{0:.2f}** ___________  Cardiac Drift : {1:.2f}
'''.format(run.get('TSS'), run.get('cardiac_drift')))
    else:
        return '# There is no heartrate data for this run'


@app.callback(
    Output('graph2-with-dropdown', 'figure'),
    [Input('graph4', 'clickData')],
    [_user])
@cache.memoize(timeout=timeout*30)
def update_figure2(clickData, user):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = str(cached_training_summary(user_id=user)[-1]['time'])
    filtered_df, filtered_speed, filtered_hr, _ = search_run(user_id=user, time=selected_date)

    traces = []
    zones = sorted(filtered_speed.keys())

    traces.append(go.Bar(
        x=zones,
        y=[filtered_speed[zone] for zone in zones],
        name='Pace Zones',
        text=zones_text_pace(),
        marker=dict(color=colors[0])
    ))
    if filtered_hr:
        traces.append(go.Bar(y=[filtered_hr[zone] for zone in zones],
                             x=zones, name='HR', text=zones_text_hr(),
                             marker=dict(color=colors[1])))

    return go.Figure({
        'data': traces,
        'layout': go.Layout(
            title='Pace and HR Zones', hovermode="closest", yaxis={'title': 'Minutes in Zone', 'hoverformat': '.2f'}
        )
    }).to_dict()


@app.callback(
    Output('graph3', 'figure'),
    [Input('graph4', 'clickData')],
    [_user])
@cache.memoize(timeout=timeout*30)
def update_figure3(clickData, user):
    if clickData:
        selected_date = clickData['points'][0]['text'].split('<br>')[2]
    else:
        selected_date = str(cached_training_summary(user_id=user)[-1]['time'])
    filtered_df, _, _, _ = search_run(user_id=user, time=selected_date)
    return plot_training_loads(selected_date.split(' ')[0], user_id=user).to_dict()


@app.callback(
    Output('click-data', 'children'),
    [Input('graph4', 'clickData')])
def display_click_data(clickData):
    return json.dumps(clickData['points'][0]['text'].split('<br>')[2].split(' ')[0], indent=2)


@app.callback(
    Output('graph4', 'figure'),
    [Input('week-start-dropdown', 'value'), Input('week-end-dropdown', 'value')],
    [_user])
@cache.memoize(timeout=timeout)
def update_figure4(start, end, user):
    df = pd.DataFrame(cached_training_summary(user_id=user))
    return heat_map_running(df, start, end).to_dict()


app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/dZVMbK.css'})

if __name__ == '__main__':
    app.run_server(debug=True)
