import json

import flask
import httplib2

from apiclient import discovery
from oauth2client import client

from pymongo import MongoClient

app = flask.Flask(__name__)
mongo_client = MongoClient('mongo', 27017)
db = mongo_client.gmail_downloader


@app.route('/')
def index():
    return "Hello world"

@app.route('/users/<client_id>/messages')
def list_messages(client_id):
    user_credentials = db.credentials.find({'client_id': client_id})
    if not user_credentials:
      return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(json.dumps(user_credentials[0]['credentials']))
    if credentials.access_token_expired:
      return flask.redirect(flask.url_for('oauth2callback'))
    else:
      http = credentials.authorize(httplib2.Http())
      service = discovery.build('gmail', 'v1', http=http)

    messages = service.users().messages().list(userId='me').execute()['messages']
    return json.dumps(messages)

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
