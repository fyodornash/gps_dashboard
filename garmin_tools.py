import os
import numpy as np
import pandas as pd
from datetime import timedelta, datetime
from urllib.request import Request, urlopen
import json

import plotly.offline as py
import plotly.graph_objs as go

from db_utils import mongo_decorator

pd.core.common.is_list_like = pd.api.types.is_list_like

colors = ['#222222', '#be3030', '#ff7100', '#7b3c3c', '#db5f29']
MAXHR = 190
LTHR = 175
LT_SPEED = 14.0
JF_SPEED_BINS = LT_SPEED / np.array([5, 1.29, 1.14, 1.06, 0.99, 0.97, 0.9, 0.5])

RHR = 50
JF_BINS = np.array([0, 0.85, 0.9, 0.95, 1.00, 1.03, 1.06, 1.5]) * LTHR
JF_ZONES = ['Zone 1', 'Zone 2', 'Zone 3', 'Zone 4', 'Zone 5a', 'Zone 5b', 'Zone 5c']
HR_TSS = {'Zone 1': 30, 'Zone 2': 55, 'Zone 3': 70, 'Zone 4': 80, 'Zone 5a': 100, 'Zone 5b': 120, 'Zone 5c': 140}
CTL_WINDOW = 42
ATL_WINDOW = 7

JF_BINS

failed_track = []


def cardiac_drift(df):
    halfway = int(df.shape[0] / 2)
    df1 = df[df.index < halfway]
    df2 = df[df.index >= halfway]
    x = (df1['Distance'].max() / (np.average(df1.Heartrate) * max(df1.time) / 60)) / (
            df2['Distance'].max() / (np.average(df2.Heartrate) * max(df2.time) / 60))

    return 100 * (x - 1)


def create_zones_increasing(a, b):
    if a == '':
        return '(< ' + b + ') bpm'
    if b == '':
        return '(> ' + a + ') bpm'
    return '(' + ' - '.join([a, b]) + ') bpm'


def zones_text_hr():
    r = list(JF_BINS.astype('int').astype('str'))
    r[0], r[-1] = '', ''
    return [create_zones_increasing(a, b) for a, b in zip(r, r[1:])]


def create_zones_decreasing(a, b):
    if a == '':
        return '(> ' + b + ') min/km'
    if b == '':
        return '(< ' + a + ') min/km'
    return '(' + ' - '.join([a, b]) + ') min/km'


def zones_text_pace():
    minutes, seconds = divmod((3600 / JF_SPEED_BINS).astype('int'), 60)
    t = [("%02d:%02d" % (m, s)) for m, s in zip(list(minutes), list(seconds))]
    t[0], t[-1] = '', ''
    return [create_zones_decreasing(a, b) for a, b in zip(t, t[1:])]


def get_hr_zones(df):
    y = pd.Series(pd.cut(df.Heartrate, bins=JF_BINS, labels=JF_ZONES, retbins=False))
    return y.value_counts().reindex(JF_ZONES)


def get_speed_zones(df):
    y = pd.Series(pd.cut(df.Speed, bins=JF_SPEED_BINS, labels=JF_ZONES, retbins=False))
    return y.value_counts().reindex(JF_ZONES)


def get_hr_zones_minutes(df):
    y = pd.Series(pd.cut(df.Heartrate, bins=JF_BINS, labels=JF_ZONES, retbins=False))
    return dict(y.value_counts().reindex(JF_ZONES) / 60)


def get_speed_zones_minutes(df):
    y = pd.Series(pd.cut(df.Speed, bins=JF_SPEED_BINS, labels=JF_ZONES, retbins=False))
    return dict(y.value_counts().reindex(JF_ZONES) / 60)


def plot_hr_zones(df):
    y = pd.Series(pd.cut(df.Heartrate, bins=JF_BINS, labels=JF_ZONES, retbins=False))
    trace1 = go.Bar(y=(y.value_counts().reindex(JF_ZONES) / 60), x=JF_ZONES)
    data = [trace1]
    layout = go.Layout(title='HR Zones')
    fig = go.Figure(data=data, layout=layout)
    py.plot(fig, filename='basic-bar')
    return


def plot_speed_zones(df):
    y = pd.Series(pd.cut(df.Speed, bins=JF_SPEED_BINS, labels=JF_ZONES, retbins=False))
    trace1 = go.Bar(y=(y.value_counts().reindex(JF_ZONES) / 60), x=JF_ZONES, text=zones_text_pace())
    data = [trace1]
    layout = go.Layout(title='Speed Zones')
    fig = go.Figure(data=data, layout=layout)
    py.plot(fig, filename='basic-bar')
    return


def plot_speed_vs_hr(df):
    speed = pd.Series(pd.cut(df.Speed, bins=JF_SPEED_BINS, labels=JF_ZONES, retbins=False))
    hr = pd.Series(pd.cut(df.Heartrate, bins=JF_BINS, labels=JF_ZONES, retbins=False))
    trace1 = go.Bar(y=(speed.value_counts().reindex(JF_ZONES) / 60), x=JF_ZONES, name='Pace', text=zones_text_pace())
    trace2 = go.Bar(y=(hr.value_counts().reindex(JF_ZONES) / 60), x=JF_ZONES, name='HR')
    data = [trace1, trace2]
    layout = go.Layout(title='Pace and HR Zones <br>Stress Score : {0:.2f}<br>Cardiac Drift :{1:.2f}'.format(TSS(df),
                                                                                                             cardiac_drift(
                                                                                                                 df)),
                       barmode='group')
    fig = go.Figure(data=data, layout=layout)
    # py.plot(fig, filename='/home/michael/garmin/michael_data/pace_hr_zones')
    return fig


def TSS(df):
    x = get_hr_zones(df)
    TSS = 0
    for zone in x.keys():
        TSS += HR_TSS[zone] * x[zone] / 3600
    return TSS


def get_training_log(week_df):
    row = [0] * 7
    xs = {d.day: d.Stress for d in week_df.itertuples()}
    for k in xs.keys():
        row[k] = xs[k]
    return row


def get_training_log_with_text(week_df):
    row = [0] * 7
    text_row = ['Rest Day'] * 7
    xs = {d.day: [d.TSS, d.text] for d in week_df.itertuples()}
    for k in xs.keys():
        row[k] = xs[k][0]
        text_row[k] = xs[k][1]
    return row, text_row


@mongo_decorator
def get_training_summary(db=None):
    '''returns a list of ('TSS',str(datetime),duration,distance) dicts'''
    query = {'$project': {'df': {'$slice': ['$df', -1]}, 'TSS': 1, 'time': 1}}
    sort = {'$sort': {'time': 1}}
    test = list(db.runsy.aggregate([query, sort]))
    return [{'TSS': t.get('TSS'), 'time': datetime.strptime(str(t['time']), '%Y-%m-%d %H:%M:%S'),
             'Distance': float(t['df'][0]['Distance']) / 1000, 'duration': float(t['df'][0]['time']) / 60} for t in test
            if t.get('TSS')]


@mongo_decorator
def get_TSSes():
    '''returns a list of list('TSS',str(datetime)) lists'''
    sort = {'$sort': {'time': 1}}
    rs = list(db.runsy.aggregate([{'$match': {}}, sort]))
    #    rs = list(db.runs.find({},{'TSS':1,'time':1}))
    return [[r.get('TSS'), datetime.strptime(str(r.get('time')), '%Y-%m-%d %H:%M:%S')] for r in rs if r.get('TSS')]


@mongo_decorator
def search_run(db=None, time=None):
    t = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
    print(time, t)
    if os.environ.get('MONGO_URL'):
        time = time
    else:
        time = t
    run = db.runsy.find_one({'time': time})

    d = str(run['time']).split()[0]
    d = str(run['time']).split()[0]
    return df_run(run), run['speed_zones'], run.get('hr_zones'), run


def df_run(run):
    try:
        return pd.DataFrame(run['df'])
    except ValueError:
        df = pd.DataFrame(json.loads(run['df'].replace("'", '"')))
        df.Time = pd.to_datetime(df.Time)
    return df


def plot_training_loads(TSSes, date=None):
    TL_df = pd.DataFrame(get_training_summary())
    TL_df = TL_df.sort_values(by='time')
    TSSes = np.array(TL_df[['TSS', 'time']])

    if date == None:
        date = str(TSSes[-1][1]).split()[0]
    CTL = pd.DataFrame(training_loads(TSSes, 42), columns=['CTL', 'time'])
    ATL = pd.DataFrame(training_loads(TSSes, 7), columns=['ATL', 'time'])
    TL_df['Fatigue'] = ATL.ATL
    TL_df['Fitness'] = CTL.CTL
    TL_df['Form'] = TL_df.Fitness - TL_df.Fatigue
    TL_df['text'] = TL_df.Distance.round(2).astype('str') + ' km<br>' + TL_df.duration.round(2).astype('str') + ' mins'

    start_date = str(TSSes[18][1]).split()[0]
    cols = ['Form', 'Fatigue', 'Fitness', 'TSS']

    traces = [go.Scatter(y=TL_df[col], x=TL_df['time'], name=col) if not col == 'TSS'
              else go.Scatter(y=TL_df[col], x=TL_df['time'], name=col, text=TL_df['text']) for col in cols]

    data = traces
    layout = go.Layout(
        title='Training Loads',
        colorway=colors,
        annotations=[
            dict(
                x=date,
                y=-0,
                xref='x',
                yref='y',
                text='Selected Run',
                showarrow=True,
                arrowhead=0,
                ax=0,
                ay=-150
            )],
        xaxis=dict(
            range=[TL_df['time'][18], TL_df['time'].max()],
            type='date')
    )
    fig = go.Figure(data=data, layout=layout)

    return fig


def update_TSSes(df):
    TSSes = get_TSSes()
    if df.Time[0] in [t[1] for t in TSSes]:
        print('No update was necessary to TSSes')
    else:
        t = TSS(df)
        print('adding stress score of {0:.2f} from run at {1} to TSSes'.format(t, str(df.Time[0])))
        TSSes.append([t, df.Time[0]])
        x = pd.DataFrame(TSSes)
        x.to_csv('/home/michael/garmin/michael_data/test.csv', index=False, header=False)
        record = create_record(df)
        insert_runs_mongo([record])
        post_runs_gcloud(record)


@mongo_decorator
def insert_runs_mongo(records=None,db=None):
    result = db.runsy.insert_many(records)
    print('Inserted records:')
    print(result.inserted_ids)


def post_runs_gcloud(record):
    record['time'] = str(record['time'])
    url = 'http://35.203.51.139/upload'  # Set destination URL here
    req = Request(url)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    jsondata = json.dumps(record)
    jsondataasbytes = jsondata.encode('utf-8')  # needs to be bytes
    req.add_header('Content-Length', len(jsondataasbytes))
    # print (jsondataasbytes)
    response = urlopen(req, jsondataasbytes)
    # json2 = urlopen(response).read().decode()
    print('uploading to cloud')
    print(response)
    return response


@mongo_decorator
def get_training_summary(db=None):
    '''returns a list of ('TSS',str(datetime),duration,distance) dicts'''
    query = {'$project': {'df': {'$slice': ['$df', -1]}, 'TSS': 1, 'time': 1}}
    test = list(db.runsy.aggregate([query]))
    return [{'TSS': t.get('TSS'), 'time': datetime.strptime(str(t['time']), '%Y-%m-%d %H:%M:%S'),
             'Distance': float(t['df'][0]['Distance']) / 1000, 'duration': float(t['df'][0]['time']) / 60} for t in test
            if t.get('TSS')]


def get_training_log_with_text_and_date(week_df):
    row = [0] * 7
    text_row = ['Rest Day'] * 7
    dates_row = [None] * 7
    xs = {d.day: [d.TSS, d.text, d.time] for d in week_df.itertuples()}
    for k in xs.keys():
        row[k] = xs[k][0]
        text_row[k] = xs[k][1]
        dates_row[k] = xs[k][2]

    return (row, text_row, dates_row)


def add_weeks(df):
    df['text'] = df.Distance.round(2).astype('str') + ' kms<br>' + df.duration.round(2).astype(
        'str') + ' mins' + '<br>' + df.time.astype('str')
    df['week'] = df.time.apply(lambda x: datetime.strptime('{0}-{1}-{2}'.format(x.year, x.week, 1), '%Y-%W-%w')).astype(
        'str')
    df['week2'] = 'Week of ' + df.time.apply(
        lambda x: datetime.strptime('{0}-{1}-{2}'.format(x.year, x.week, 1), '%Y-%W-%w')).apply(
        lambda y: y.strftime('%B %-d'))
    return df


def heat_map_running(df, start, end):
    print('start = {} and end = {}'.format(start, end))
    df = add_weeks(df)

    df['day'] = df.time.apply(lambda x: x.dayofweek)
    df = df[df.week.isin(df.week.unique()[start: end + 1])]
    colorscale = [
        [0, 'rgba(198,198,198,1)'],
        [1, 'rgb(178, 34, 34)']
    ]

    z = []
    texts = []
    custom_data = []
    x = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for week in df.week.unique():
        filt_df = df[df.week == week]
        z_row, t_row, c_row = get_training_log_with_text_and_date(filt_df)
        z.append(z_row)
        texts.append(t_row)
        custom_data.append(c_row)

    trace = go.Heatmap(z=z,
                       x=x,
                       y=df.week2.unique(),
                       text=texts,
                       hoverinfo='z+text',
                       colorscale=colorscale,
                       customdata=custom_data)
    layout = go.Layout(title='Training Stress Calendar', margin=dict(l=120))
    data = [trace]
    return go.Figure(data=data, layout=layout)


def create_record(df):
    record = {}
    record['time'] = df.Time[0]
    df.Time = pd.DatetimeIndex(df.Time).astype(np.int64) // 10 ** 9
    record['df'] = df.to_dict('records')
    record['speed_zones'] = get_speed_zones_minutes(df)
    record['user_data'] = {'max_hr': MAXHR, 'lt_hr': LTHR, 'lt_speed': LT_SPEED}

    if 'Heartrate' in df.columns:
        tss = TSS(df)
        record['TSS'] = tss
        record['hr_zones'] = get_hr_zones_minutes(df)
        record['cardiac_drift'] = cardiac_drift(df)
    return record


def analize_run(df):
    print('Stress Score : {0:.2f}'.format(TSS(df)))
    print('Cardiac Drift : {0:.2f}'.format(cardiac_drift(df)))


def training_loads(TSSes, window):
    """TSSes must be a list of tuples. t[0] is tss and t[0] is timestamp of the tss """
    TLs = []
    for i in TSSes:
        w = list(map(lambda a: (a[0], i[1] >= a[1] and i[1] - a[1] < timedelta(window)), TSSes))
        filtered_w = list(filter(lambda x: x[1], w))
        TLs.append([sum(list(map(lambda x: x[0], filtered_w))) / window, i[1]])
    return TLs
