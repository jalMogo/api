# Set up private key using multi-stage Dockerfile:
# https://vsupalov.com/build-docker-image-clone-private-repo-ssh-key/

# this is our first build stage, it will not persist in the final image
FROM ubuntu as intermediate

# install git
RUN apt-get update
RUN apt-get install -y git

# add credentials on build
ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa
RUN chmod 0600 /root/.ssh/id_rsa

# make sure your domain is accepted
RUN touch /root/.ssh/known_hosts
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

RUN git clone git@github.com:jalMogo/api.git
RUN cd api && git checkout master


###########################################################
# Dockerfile to build Python WSGI Application Containers
# Based on Debian
############################################################

# Set the base image to Debian
FROM python:3.7.5-stretch

# File Author / Maintainer
MAINTAINER Luke Swart <luke@mapseed.org>

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y tar curl wget dialog net-tools build-essential gettext

# Install Python and Basic Python Tools
RUN apt-get install -y python-dev python-distribute python-pip

# Install Postgres/PostGIS dependencies:
RUN apt-get install -y python-psycopg2 postgresql libpq-dev postgresql-9.6-postgis-2.3 postgis postgresql-9.6


# Move the repo from our intermediate image into our final image:
COPY --from=intermediate /api /api

# # for local testing, cd into project root and uncomment this line:
# ADD . api

# Get pip to download and install requirements:
RUN pip install -r /api/requirements.txt

# Expose ports
EXPOSE 8010

# Set the default directory where CMD will execute
WORKDIR /api

RUN mkdir static
VOLUME /api/static

# Set the default command to execute
# when creating a new container
# ex:
# CMD python server.py
# or:
# CMD sh -c "python src/manage.py collectstatic --noinput && gunicorn wsgi:application -w 3 -b 0.0.0.0:8010"
CMD /api/start.sh
