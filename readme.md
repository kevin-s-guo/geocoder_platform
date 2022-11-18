## Geocoder Platform
### Docker setup
In order to deploy the geocoder platform, download the `docker-compose.yml` file. In the directory containing that file, run the following command.

``$ docker compose pull``

This will pull the two images required. 

Before the web app will work, the PostgreSQL database will need to be set up.

First, create and start the database container with docker compose.

``$ docker compose up -d db``

Next, run the setup shell script. 

``$ docker exec geocoder-platform-db sh load_default.sh``

`load_default.sh` will install PostGIS (the spatial database extension), download 2020 census data, import 2010 block-group boundaries, and create the necessary tables for the web app. Depending on download speed, this may take hours. The full US Census data will take up approximately 100 gigabytes of storage.

When this is done, the python web server container can be started with the following command.

``$ docker compose up``

If everything worked according to plan, navigating to `localhost:7001/docs` in a web browser should show the API documentation page.

