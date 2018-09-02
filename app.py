from __future__ import print_function
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from textwrap import dedent
from garmin_tools import plot_training_loads
from time import time
import json
import datetime

from pymongo import MongoClient,InsertOne,UpdateOne

from flask import Flask,request

import sys

def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

app = Flask('update_db')
server = app.server

@app.route('/upload/',methods = ['POST'])
def result():
    with MongoClient(os.environ.get('MONGO_URL')) as client:
        db = client.garmin
        record = request.get_json()
        record['time'] = datetime.datetime.fromtimestamp(float(record['time'])).strftime('%Y-%m-%d %H:%M:%S')
#        for k in record.keys():
#            try:
#                record[k] = json.loads(record[k].replace("'",'"'))
#            except ValueError:
#                pass
        #record = {a:b for a,b in zip(request.form.keys(),request.form.values())}
        db.runsy.insert_many([record])
        return 'Received'
