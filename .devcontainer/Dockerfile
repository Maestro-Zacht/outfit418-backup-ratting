ARG AA_DOCKER_TAG
FROM $AA_DOCKER_TAG

RUN cd /home/allianceauth
COPY .devcontainer/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . /workspace
RUN ln -s /workspace/outfit418_backup_ratting myauth/outfit418_backup_ratting

RUN allianceauth update myauth