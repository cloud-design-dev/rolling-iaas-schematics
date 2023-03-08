FROM python:3.10.10-slim-bullseye

WORKDIR /usr/src/app

COPY requirements.txt ./
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION python
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV IBMCLOUD_API_KEY $IBMCLOUD_API_KEY
ENV WORKSPACE_ID $WORKSPACE_ID
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION python

CMD [ "python", "./main.py" ]
