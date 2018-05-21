#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
import logging
import time
import sqlite3
import _thread
import yaml

from matrix_client.client import MatrixClient
from matrix_client.client import MatrixHttpApi
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema
from datetime import date, datetime
from bottle import request, route, run, template


@route('/<room>')
def index(room):
    return board(room=room)

def board(room):
    try:
        roomname = matrix.get_room_name(room)
    except:
        return "no room access"
    db = sqlite3.connect('db')
    cur = db.cursor()
    r = (room,)
    cur.execute("SELECT * FROM messages WHERE roomid = ? ORDER BY date DESC LIMIT 5", r)
    rows = cur.fetchall()
    lines = []
    for row in reversed(rows):
        lines.append({
            'sender': row[3],
            'message': row[4]
        })
    db.close()
    tvars = {
        'roomname': roomname.get('name'),
        'lines': lines,
        'color': request.query.get('color'),
        'riot': request.query.get('riot') or 'https://riot.im/app',
        'room': room
    }
    return template('board.html', tvars)

# Called when a message is received.
def on_message(room, event):
    if event['type'] == "m.room.message":
        if event['content']['msgtype'] == "m.text":
            message = event['content']['body'].encode('utf8', 'ignore')
            sender = matrix.get_display_name(event['sender'])
            now = datetime.now()

            db = sqlite3.connect('db')
            cur = db.cursor()
            cur.execute('INSERT INTO messages(date, roomid, sender, message) VALUES(?,?,?,?)', (now, event['room_id'], sender, message))
            db.commit()
            db.close()



def main(host, username, password):
    client = MatrixClient(host)
    rooms = client.get_rooms()

    try:
        db = sqlite3.connect('db')
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, date TEXT, roomid TEXT, sender TEXT, message TEXT)''')
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    def on_invite(room_id, state):
        print ("joining room " + room_id)
        room = client.join_room(room_id)
        room.add_listener(on_message)

    try:
        token = client.login_with_password(username, password)
        global matrix
        matrix = MatrixHttpApi(host, token)
    except MatrixRequestError as e:
        print(e)
        if e.code == 403:
            print("Bad username or password.")
            sys.exit(4)
        else:
            print("Check if server details are correct.")
            sys.exit(2)
    except MissingSchema as e:
        print("Bad URL format.")
        print(e)
        sys.exit(3)

    for room in rooms:
        try:
            roomname = matrix.get_room_name(room)
            print ("Already in room " + roomname['name'])
            room_to_listen = client.join_room(room)
            room_to_listen.add_listener(on_message)
        except MatrixRequestError as e:
            print(e)
            if e.code == 400:
                print("Room ID/Alias in the wrong format")
                sys.exit(11)
            else:
                print("Couldn't find room.")
                sys.exit(12)

    client.add_invite_listener(on_invite)
    client.start_listener_thread()

    while True:
        time.sleep(30)

with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    print(cfg)
    _thread.start_new_thread(main, (cfg['server'], cfg['username'], cfg['password']))
    run(host='0.0.0.0', port=1337)


