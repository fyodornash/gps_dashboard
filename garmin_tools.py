
# coding: utf-8

# In[1]:

import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import ChainMap
from sklearn import linear_model
from datetime import timedelta,datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


import plotly.offline as py
import plotly.graph_objs as go
pd.core.common.is_list_like = pd.api.types.is_list_like
import pandas_datareader.data as web
    
from pymongo import MongoClient,InsertOne,UpdateOne
client = MongoClient('localhost',27017) 
db = client.garmin

# In[2]:

MAXHR = 190
LTHR = 175
LT_SPEED= 14.0
JF_SPEED_BINS = LT_SPEED/np.array([5,1.29,1.14,1.06,0.99,0.97,0.9,0.5])

RHR = 50
JF_BINS = np.array([0,0.85,0.9,0.95,1.00,1.03,1.06,1.5])*LTHR
JF_ZONES=['Zone 1','Zone 2','Zone 3','Zone 4','Zone 5a','Zone 5b','Zone 5c']
HR_TSS = {'Zone 1':30,'Zone 2':55,'Zone 3':70,'Zone 4':80,'Zone 5a':100,'Zone 5b':120,'Zone 5c':140}
CTL_WINDOW=42
ATL_WINDOW=7

JF_BINS

failed_track =[]
def get_track(x):
    try:
        return x.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Track').getchildren()
    except AttributeError:
        print(x,'test')
        failed_track.append(x)


# In[20]:
def create_df(clean_dps):
    df = pd.DataFrame()
    
    try:
        time = [element['Time'].text for element in clean_dps]
        df['Time']=time
    except KeyError:
        print('no time data for index {0}'.format(i))  
    try:
        altitude = [float(element['AltitudeMeters'].text) for element in clean_dps]
        df['Altitude']=altitude
    except KeyError:
        print('no altitude data for index {0}'.format(i))  
    try:
        distance = [float(element['DistanceMeters'].text) for element in clean_dps]
        df['Distance'] = distance
    except KeyError:
        print('no distance data for index {0}'.format(i))
    
    try:
        heart_rate =[float(element['HeartRateBpm'].getchildren()[0].text) for element in clean_dps]
        df['Heartrate'] = heart_rate
    except KeyError:
        print('no heartrate data for index {0}'.format(i))
    return df


def clean_df(df,gaussian):
    df.Time = pd.to_datetime(df.Time)
    x = (np.array(df.Time.diff())/1000000000.0).astype('float32')
    np.cumsum(x)
    y = df.Distance.diff()/x
    x[0]=0
    df['time'] = np.cumsum(x)
    y[0]=0
    y[5:] = np.convolve(gaussian,y)[24:]
    y[5:] = np.convolve(gaussian,y)[24:]
    df['Speed'] = y*3.6
    #df['Gradient']
    if 'Heartrate' in df.columns:
        z = np.convolve(gaussian,df.Heartrate)
        df.Heartrate = z[19:]
        df['Efficiency'] = df.Speed*1000/(df.Heartrate*60) #meters/beat
        df.Efficiency = df.Efficiency.fillna(0)
        df.Efficiency[df.Efficiency>2] =0
        
    return df

def cardiac_drift(df):
    halfway = int(df.shape[0]/2)
    df1 = df[df.index<halfway]
    df2 = df[df.index>=halfway]
    x = (df1['Distance'].max()/(np.average(df1.Heartrate)*max(df1.time)/60))/(df2['Distance'].max()/(np.average(df2.Heartrate)*max(df2.time)/60))
    
    return 100*(x-1)



def create_zones_increasing(a,b):
    if a == '':
        return '(< ' + b + ') bpm'
    if b == '':
        return '(> ' + a + ') bpm'
    return '(' + ' - '.join([a,b])+ ') bpm'
def zones_text_hr():
    r = list(JF_BINS.astype('int').astype('str'))
    r[0],r[-1]='',''
    return [create_zones_increasing(a,b) for a,b in zip(r,r[1:])]

def create_zones_decreasing(a,b):
    if a == '':
        return '(> ' + b + ') min/km'
    if b == '':
        return '(< ' + a + ') min/km'
    return '(' + ' - '.join([a,b])+ ') min/km'

def zones_text_pace():
    minutes,seconds = divmod((3600/JF_SPEED_BINS).astype('int'),60)
    t = [("%02d:%02d" % ( m, s)) for m,s in zip(list(minutes),list(seconds))]
    t[0],t[-1]='',''
    return [create_zones_decreasing(a,b) for a,b in zip(t,t[1:])]






def get_hr_zones(df):
    y = pd.Series(pd.cut(df.Heartrate,bins=JF_BINS,labels=JF_ZONES,retbins=False))
    return y.value_counts().reindex(JF_ZONES)

def get_speed_zones(df):
    y = pd.Series(pd.cut(df.Speed,bins=JF_SPEED_BINS,labels=JF_ZONES,retbins=False))
    return y.value_counts().reindex(JF_ZONES)

def get_hr_zones_minutes(df):
    y = pd.Series(pd.cut(df.Heartrate,bins=JF_BINS,labels=JF_ZONES,retbins=False))
    return dict(y.value_counts().reindex(JF_ZONES)/60)

def get_speed_zones_minutes(df):
    y = pd.Series(pd.cut(df.Speed,bins=JF_SPEED_BINS,labels=JF_ZONES,retbins=False))
    return dict(y.value_counts().reindex(JF_ZONES)/60)

# In[27]:

def plot_hr_zones(df):
    y = pd.Series(pd.cut(df.Heartrate,bins=JF_BINS,labels=JF_ZONES,retbins=False))
    trace1 = go.Bar(y = (y.value_counts().reindex(JF_ZONES)/60),x =JF_ZONES)
    data = [trace1]
    layout = go.Layout(title='HR Zones')
    fig = go.Figure(data=data, layout=layout)
    py.plot(fig, filename='basic-bar')
    return


# In[28]:

def plot_speed_zones(df):
    y = pd.Series(pd.cut(df.Speed,bins=JF_SPEED_BINS,labels=JF_ZONES,retbins=False))
    trace1 = go.Bar(y = (y.value_counts().reindex(JF_ZONES)/60),x =JF_ZONES,text = zones_text_pace(JF_SPEED_BINS))
    data = [trace1]
    layout = go.Layout(title='Speed Zones')
    fig = go.Figure(data=data, layout=layout)
    py.plot(fig, filename='basic-bar')
    return


# In[44]:

def plot_speed_vs_hr(df):
    speed = pd.Series(pd.cut(df.Speed,bins=JF_SPEED_BINS,labels=JF_ZONES,retbins=False))
    hr = pd.Series(pd.cut(df.Heartrate,bins=JF_BINS,labels=JF_ZONES,retbins=False))
    trace1 = go.Bar(y = (speed.value_counts().reindex(JF_ZONES)/60),x =JF_ZONES,name ='Pace',text = zones_text_pace(JF_SPEED_BINS))
    trace2 = go.Bar(y = (hr.value_counts().reindex(JF_ZONES)/60),x =JF_ZONES, name ='HR')
    data = [trace1,trace2]
    layout = go.Layout(title='Pace and HR Zones <br>Stress Score : {0:.2f}<br>Cardiac Drift :{1:.2f}'.format(TSS(df),cardiac_drift(df)),barmode='group')
    fig = go.Figure(data=data, layout=layout)
    #py.plot(fig, filename='/home/michael/garmin/michael_data/pace_hr_zones')
    return fig


def TSS(df):
    x = get_hr_zones(df)
    TSS = 0
    for zone in x.keys():
        TSS += HR_TSS[zone]*x[zone]/3600
        
    return TSS

def get_TSSes():
    x= pd.read_csv('/home/michael/garmin/michael_data/test.csv',header=None)
    x[1]= pd.to_datetime(x[1])
    return np.array(x).tolist()

def plot_training_loads(TSSes,date = None):
    if date == None:
        date = str(TSSes[-1][1]).split()[0]
    ATLs = training_loads(TSSes,ATL_WINDOW)
    CTLs = training_loads(TSSes,CTL_WINDOW)
    TSBs = [(b[0] - a[0],a[1]) for a,b in zip(ATLs,CTLs)]
    TSS_array = np.array(TSSes)[:,0]
    ATLs = np.array(ATLs)
    CTLs = np.array(CTLs)
    TSBs = np.array(TSBs)
    table = np.array([ATLs[:,0],CTLs[:,0],TSBs[:,0],TSS_array,ATLs[:,1]])
    loads = pd.DataFrame(table.T,columns = ['Fatigue','Fitness','Form','Stress','Date'])
    loads.Date = pd.to_datetime(loads.Date)
    dloads = loads
    start_date = str(TSSes[18][1]).split()[0]
    trace1 = go.Scatter(y = dloads['Fitness'],x =dloads['Date'],name = 'Fitness')
    trace2 = go.Scatter(y = dloads['Form'],x =dloads['Date'], name = 'Form')
    trace3 = go.Scatter(y = dloads['Fatigue'],x =dloads['Date'],name = 'Fatigue')
    trace4 = go.Scatter(y = dloads['Stress'],x =dloads['Date'],name = 'Stress')

    data = [trace1,trace2,trace3,trace4]
    layout = go.Layout(title='Training Loads',annotations=[
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
        xaxis = dict(range = [loads['Date'][18:].min(),loads['Date'].max()])
     )
    fig = go.Figure(data=data, layout=layout)
    #py.plot(fig,filename='/home/michael/garmin/michael_data/training_loads')
    return fig

def update_TSSes(df):
    TSSes = get_TSSes()
    if df.Time[0] in [t[1] for t in TSSes]:
        print('No update was necessary to TSSes')
    else:
        t = TSS(df)
        print('adding stress score of {0:.2f} from run at {1} to TSSes'.format(t,str(df.Time[0])))
        TSSes.append([t,df.Time[0]])
        x = pd.DataFrame(TSSes)
        x.to_csv('/home/michael/garmin/michael_data/test.csv',index=False,header=False)
        record = create_record(df)
        insert_runs_mongo([record])
        post_runs_gcloud(record)
        

def insert_runs_mongo(records):
    result = db.runs.insert_many(records)
    print('Inserted records:')
    print(result.inserted_ids)
    
def post_runs_gcloud(record):   
    url = 'http://35.203.124.245/upload' # Set destination URL here
    request = Request(url, urlencode(record).encode())
    json = urlopen(request).read().decode()
    print('uploading to cloud')
    print(json)        


def create_record(df):
    record = {}
    record['df'] = df.to_dict('records')
    record['time'] = df.Time[0]
    record['speed_zones'] = get_speed_zones_minutes(df)
    record['user_data'] = {'max_hr':MAXHR,'lt_hr':LTHR,'lt_speed':LT_SPEED}
    if 'Heartrate' in df.columns:
        record['TSS'] = TSS(df)
        record['hr_zones'] = get_hr_zones_minutes(df)
        record['cardiac_drift'] = cardiac_drift(df)
    return record        
        
def analize_run(df):
    print('Stress Score : {0:.2f}'.format(TSS(df)))
    print('Cardiac Drift : {0:.2f}'.format(cardiac_drift(df)))
    plot_speed_vs_hr(df)
    TSSes =get_TSSes()
    plot_training_loads(TSSes)

def training_loads(TSSes,window):
    """TSSes must be a list of tuples. t[0] is tss and t[0] is timestamp of the tss """
    TLs = []
    for i in TSSes:
        w = list(map(lambda a: (a[0],i[1]>=a[1] and i[1]-a[1]<timedelta(window)),TSSes))
        filtered_w = list(filter(lambda x: x[1],w))
        TLs.append([sum(list(map(lambda x: x[0],filtered_w)))/window,i[1]])
    return TLs
