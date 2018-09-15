import os

from pymongo import MongoClient


def mongo_decorator(func):
    def wrapper(*args, **kwargs):
        print('making mongo connection with decorator')
        with MongoClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017')) as client:
            print('sending connection to function')
            return func(db=client.garmin, **kwargs)

    return wrapper
