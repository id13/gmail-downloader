# Run

- You need to create a directory for mongodb (/opt/mongodb by default) and chown to your user (or remove the volume attribute for mongodb in docker-compose.yml) 
- `docker-compose up`
- `localhost:5000/oauth2callback`
- Connect to the flask node `docker exec -it #container_id /bin/bash`
- `cd ..`
- `python`
- `from app.tasks import fetch_messages`
- `fetch_messages.delay(#yourclientid)`
