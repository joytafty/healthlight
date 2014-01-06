#!/usr/bin/env python
import datetime
import flask
from flask import Flask, Response, render_template
import json
import nltk
import logging
import re
import random
from redis import Redis
import thread
import time
from twitter import OAuth, TwitterStream
import urllib2
import urlparse
import os
import sys
import time

logger = logging.getLogger('log')
logger.addHandler(logging.FileHandler('log.json'))
logger.setLevel(logging.INFO)

redis = Redis()

oauth = OAuth(
    os.getenv('TWITTER_TOKEN'), os.getenv('TWITTER_TOKEN_SECRET'),
    os.getenv('TWITTER_CONSUMER_KEY'), os.getenv('TWITTER_CONSUMER_SECRET')
)

twitter = TwitterStream(auth=oauth)
start = time.clock()

def stopwords():
    try:
        stop_words = stopwords.stop_words
    except AttributeError:
        try:
            stop_words = nltk.corpus.stopwords.words('english')
        except LookupError:
            nltk.download('stopwords')
            stop_words = nltk.corpus.stopwords.words('english')
        stop_words.extend(['-', ':', '.', '\'', '\',', ',', '#', '/', '@', '.,', '(', ')', 'RT', 'I', 'I''m'])
        stopwords.stop_words = stop_words
    return stop_words
        
stop_words = stopwords()
    
def stream():
    for i, tweet in enumerate(twitter.statuses.sample()):
        if 'text' in tweet:
            for word in tweet['text'].encode('utf-8').split():
                if word not in stop_words:
                    redis.zincrby('count', word, 1)
            # print '%.f (%i); %.f' % (i / (time.clock()-start), i, i / (time.clock() - start) * 3600 * 24 / 1e6)

t = thread.start_new_thread(stream, ())
    
def conv(f):
    return '%.f' % float(f)

def server():
    app = Flask(__name__, static_folder='static')
    
    @app.route('/data.csv')
    def index():
        data = redis.zrange('count', 0, 100, withscores=True, desc=True, score_cast_func=conv)
        def gen():
            yield 'key,count\n'
            for row in data:
                if row[1] > 1:
                    yield ','.join(row) + '\n'
        return Response(gen(), mimetype='text/plain')
    
    app.run('0.0.0.0', port=int(os.getenv('PORT', '80')), debug=True)
    


if __name__ == '__main__':
    server()