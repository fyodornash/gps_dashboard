from __future__ import print_function
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from textwrap import dedent
from garmin_tools import plot_training_loads
from parse import upload_xml
from time import time
import json
import datetime

from pymongo import MongoClient

from flask import Flask, request

import sys

def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)


app = Flask('update_db')


@app.route('/',methods = ['POST'])
def result():
    with MongoClient(os.environ.get('MONGO_URL')) as client:
        db = client.garmin
        json_post = request.get_json()
        xml_post = request.data
        if json_post:
            record['time'] = datetime.datetime.fromtimestamp(float(record['time'])).strftime('%Y-%m-%d %H:%M:%S')
    #        for k in record.keys():
    #            try:
    #                record[k] = json.loads(record[k].replace("'",'"'))
    #            except ValueError:
    #                pass
            #record = {a:b for a,b in zip(request.form.keys(),request.form.values())}
            db.runsy.insert_many([record])
            return 'Received'
        else:
            upload_xml(xml_post)
            return 'Received xml'

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port)
