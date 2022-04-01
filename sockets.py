#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from http import client
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent.queue import Queue
from geventwebsocket import WebSocketError
from geventwebsocket.websocket import WebSocket
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()
clients = []

def set_listener( entity, data ):
    ''' do something with the update ! '''
    # I don't know what I'm supposed to do with this 
    return

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html")

def read_ws(ws: WebSocket, client: Queue):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    while not ws.closed:
        try:        
            message = ws.receive()    
            if message == None: break

            # we got a message! update the entity
            obj = json.loads(message)
            for key in obj:
                myWorld.set(key, obj[key])

            # broadcast to all connected clients 
            for c in clients:
                c.put(message)

        except WebSocketError:
            # socket is dead
            break


@sockets.route('/subscribe')
def subscribe_socket(ws: WebSocket):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    print('press like and subscribe')
    
    # inspired by Nicholas Pufal on Stack Overflow https://stackoverflow.com/a/27072972
    # based on greenlet gist https://sdiehl.github.io/gevent-tutorial/
    # create a queue for our greenlet, and add it to our connect clients
    # spawn a greelet process to continuously read from the socker and add
    # to the queues of our connect clients! 
    client = Queue()
    clients.append(client)
    greenlet = gevent.spawn(read_ws, ws, client)

    while not ws.closed:
        try:
            # get message from our queue!
            data = client.get()

            # echo message to our client 
            ws.send(data)
        except WebSocketError:
            # socket is dead
            break

    # socket closed or died, remove from clients and end its greenlet process
    print('socket clsosed')
    clients.remove(client)
    gevent.kill(greenlet)

# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return json.dumps(myWorld.world())

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''    
    return json.dumps(myWorld.get(entity))

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    data = flask_post_json()
    for key in data: myWorld.update(entity, key, data[key])
    return json.dumps(myWorld.get(entity))

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return ('', 200)



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
