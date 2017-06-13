import json

import flask
import httplib2

from bson import json_util
from apiclient import discovery
from oauth2client import client

from pymongo import MongoClient

app = flask.Flask(__name__)
db = MongoClient('mongo', 27017).gmail_downloader
PAGE_SIZE = 5


@app.route('/')
def index():
    return "Hello world"

@app.route('/users/<client_id>/messages')
def list_messages(client_id):
    messages = db.messages.find({'client_id': client_id})[0:PAGE_SIZE]
    return flask.Response(json.dumps(list(messages), default=json_util.default),
                           mimetype='application/json')

@app.route('/users/<client_id>/attachments')
def list_attachments(client_id):
    attachments = db.attachments.find({'client_id': client_id})[0:PAGE_SIZE]
    return flask.Response(json.dumps(list(attachments), default=json_util.default),
                           mimetype='application/json')
@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        scope='https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.profile',
        redirect_uri=flask.url_for('oauth2callback', _external=True))
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('plus', 'v1', http=http)
        people_document = service.people().get(userId='me').execute()
        credentials_json = json.loads(credentials.to_json())
        db.credentials.update_one({'client_id': people_document['id']}, {'$set': {'credentials': credentials_json }}, upsert=True)
        return json.dumps({'client_id': people_document['id']})


if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = False
    app.run(host='0.0.0.0')
