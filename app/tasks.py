from .celery import app
import json
import time
import httplib2
import os.path

from apiclient import discovery
from oauth2client import client

from pymongo import MongoClient
db = MongoClient('mongo', 27017).gmail_downloader
AUTHORIZED_FILE_TYPES = ['.jpg', '.png', '.pdf', '.jpeg', '.ppt', '.pptx', '.doc', '.docx']
MAX_FILE_SIZE = 8000000

def google_credentials(client_id):
    user_credentials = db.credentials.find({'client_id': client_id})
    credentials = client.OAuth2Credentials.from_json(json.dumps(user_credentials[0]['credentials']))
    return credentials.authorize(httplib2.Http())

@app.task
def download_attachment(client_id, message_id, attachment_id, filename, mime_type):
    http = google_credentials(client_id)
    service = discovery.build('gmail', 'v1', http=http)
    attachment = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id).execute()
    db.attachments.update({
            'client_id': client_id,
            'attachment_id': attachment_id,
        }, { "$set": {
                'filename': filename,
                'mime_type': mime_type,
                'data': attachment['data'],
                'size': attachment['size'],
        }},
        upsert=True,
    )

@app.task
def fetch_messages(client_id, page_token=None):
    def download_message(request_id, response, exception):
        raw_html = raw_text = None
        if exception is not None:
            raise Exception("error during message downloading")
        for part in response['payload'].get('parts', []):
            if part.get('filename', None) and (os.path.splitext(part['filename'])[1] or "").lower() in AUTHORIZED_FILE_TYPES:
                if part['body'].get('attachmentId', None) and int(part['body']['size']) <= MAX_FILE_SIZE:
                    download_attachment.delay(client_id,
                                              response['id'],
                                              part['body']['attachmentId'],
                                              part['filename'],
                                              part['mimeType'])
                continue
            else:
                if part['mimeType'] == 'text/html':
                    raw_html = part
                elif part['mimeType'] == 'text/plain':
                    raw_text = part
        db.messages.insert_one({
            'message_id': response['id'], 
            'client_id': client_id,
            'headers': response['payload']['headers'],
            'raw_text': raw_text,
            'raw_html': raw_html,
        })

    http = google_credentials(client_id)
    service = discovery.build('gmail', 'v1', http=http)
    result = service.users().messages().list(userId='me', pageToken=page_token).execute()
    messages = result['messages']

    db_messages = db.messages.find({"message_id": {"$in": [message['id'] for message in messages]}}) 
    db_message_ids = [db_message['message_id'] for db_message in db_messages]
    to_insert_messages = [message for message in messages if not message['id'] in db_message_ids]

    if result.get('nextPageToken', None):
        fetch_messages.delay(client_id, result['nextPageToken'])

    batch = service.new_batch_http_request(callback=download_message)

    for message in to_insert_messages:
        batch.add(service.users().messages().get(userId='me', id=message['id']))
    batch.execute(http=http)

