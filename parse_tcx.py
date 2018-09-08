import xml.etree.ElementTree as ET
from collections import ChainMap
from garmin_tools import *
from parse import create_df, clean_df, get_track

run_files = []
with open('/home/michael/garmin/michael_data/runs.txt') as f:
    for line in f:
        run_files.append(line.split('\n')[0])

trees = [ET.parse('/home/michael/garmin/michael_data/tcx/' + file) for file in run_files[-1:]]
roots = [tree.getroot() for tree in trees]
activities = [root.getchildren()[0].getchildren()[0] for root in roots]
running_activities = [a for a in activities if a.attrib['Sport'] == 'Running']
laps_list = [activity.findall('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Lap') for activity in
             running_activities]

tps_lists = [list(map(get_track, laps)) for laps in laps_list]

for i in range(len(tps_lists)):
    try:
        flat_tps = [[tp for tp_list in tps if tp_list for tp in tp_list] for tps in [tps_lists[i]]]
    except TypeError:
        print('There is an unhandled TypeError in an element of the list at index {0} of tps_lists'.format(i))

flat_tps_lists = [[tp for tp_list in tps if tp_list for tp in tp_list] for tps in tps_lists]
useful_tps_list = [list(filter(lambda x: len(x.getchildren()) > 1, flat_tps)) for flat_tps in flat_tps_lists]
clean_dps_list = [list(map(lambda x: list(map(lambda y: {y.tag.split('}')[1]: y}, x.getchildren())), useful_tps)) for
                  useful_tps in useful_tps_list]
clean_dps_dicts = [[dict(ChainMap(*a)) for a in clean_dp if len(a) == len(clean_dp[int(len(clean_dp) / 2)])] for
                   clean_dp in clean_dps_list]

dfs = [create_df(clean_dps) for clean_dps in clean_dps_dicts]

gaussian = np.histogram(np.random.binomial(20, 0.5, 2000), bins=20)[0] / 2000
dfs = [clean_df(df, gaussian) for df in dfs]

dfs_hr = [df for df in dfs if 'Heartrate' in df.columns]

for df in dfs_hr:
    update_TSSes(dfs_hr[-1])

    analize_run(dfs_hr[-1])

