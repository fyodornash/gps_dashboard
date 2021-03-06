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

from pymongo import MongoClient,InsertOne,UpdateOne

from flask import Flask,request

import sys

def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

app = Flask('update_db')

@app.route('/upload',methods = ['POST'])
def result():
    with MongoClient('localhost',27017) as client:
        db = client.garmin
        record = {a:b for a,b in zip(request.form.keys(),request.form.values())}
        db.runsy.insert_many([record])
    
    return 'Received'
