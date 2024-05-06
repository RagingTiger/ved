# jupyter base image
FROM quay.io/jupyter/scipy-notebook:lab-4.0.10 as base

# first turn off git safe.directory
RUN git config --global safe.directory '*'

# turn off poetry venv
ENV POETRY_VIRTUALENVS_CREATE=false

# set src target dir
WORKDIR /usr/local/src/ved

# get src
COPY . .

# get poetry in order to install development dependencies
RUN pip install poetry

# config max workers
RUN poetry config installer.max-workers 10

# create normal install layer
FROM base as normal

# do normal install
RUN poetry install -C .

# create dev install layer
FROM base as dev

# now install development dependencies
RUN poetry install --with dev -C .
