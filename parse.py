import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
from collections import ChainMap
from garmin_tools import create_record, insert_runs_mongo


def create_df(clean_dps):
    df = pd.DataFrame()

    try:
        time = [element['Time'].text for element in clean_dps]
        df['Time'] = time
    except KeyError:
        print('no time data')
    try:
        altitude = [float(element['AltitudeMeters'].text) for element in clean_dps]
        df['Altitude'] = altitude
    except KeyError:
        print('no altitude data')
    try:
        distance = [float(element['DistanceMeters'].text) for element in clean_dps]
        df['Distance'] = distance
    except KeyError:
        print('no distance data')

    try:
        heart_rate = [float(element['HeartRateBpm'].getchildren()[0].text) for element in clean_dps]
        df['Heartrate'] = heart_rate
    except KeyError:
        print('no heartrate data')
    try:
        stride_rate = [float(element['Extensions'].getchildren()[0].getchildren()[1].text) for element in clean_dps]
        df['Stride Rate'] = stride_rate
    except KeyError:
        print('no cadence data')
    return df


def clean_df(df, gaussian):
    df.Time = pd.to_datetime(df.Time)
    x = (np.array(df.Time.diff()) / 1000000000.0).astype('float32')
    np.cumsum(x)
    y = df.Distance.diff() / x
    x[0] = 0
    df['time'] = np.cumsum(x)
    y[0] = 0
    y[5:] = np.convolve(gaussian, y)[24:]
    y[5:] = np.convolve(gaussian, y)[24:]
    df['Speed'] = y * 3.6
    # df['Gradient']
    if 'Heartrate' in df.columns:
        z = np.convolve(gaussian, df.Heartrate)
        df.Heartrate = z[19:]
        df['Efficiency'] = df.Speed * 1000 / (df.Heartrate * 60)  # meters/beat
        df.Efficiency = df.Efficiency.fillna(0)
        df.Efficiency[df.Efficiency > 2] = 0

    return df


def get_track(x):
    failed_track = []
    try:
        return x.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Track').getchildren()
    except AttributeError:
        print(x, 'test')
        failed_track.append(x)


def upload_xml(xml):
    root = ET.fromstring(xml)
    activity = root.getchildren()[0].getchildren()[0]
    running_activity = activity if activity.attrib['Sport'] == 'Running' else None
    laps = running_activity.findall('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Lap')

    tps_list = list(map(get_track, laps))
    tps_lists = [tps_list]

    flat_tps_lists = [[tp for tp_list in tps if tp_list for tp in tp_list] for tps in tps_lists]
    useful_tps_list = [list(filter(lambda x: len(x.getchildren()) > 1, flat_tps)) for flat_tps in flat_tps_lists]
    clean_dps_list = [list(map(lambda x: list(map(lambda y: {y.tag.split('}')[1]: y}, x.getchildren())), useful_tps))
                      for
                      useful_tps in useful_tps_list]
    clean_dps_dicts = [[dict(ChainMap(*a)) for a in clean_dp if len(a) == len(clean_dp[int(len(clean_dp) / 2)])] for
                       clean_dp in clean_dps_list]

    dfs = [create_df(clean_dps) for clean_dps in clean_dps_dicts]

    gaussian = np.histogram(np.random.binomial(20, 0.5, 2000), bins=20)[0] / 2000
    dfs = [clean_df(df, gaussian) for df in dfs]

    dfs_hr = [df for df in dfs if 'Heartrate' in df.columns]
    record = create_record(dfs_hr[0])
    insert_runs_mongo(records=[record])
