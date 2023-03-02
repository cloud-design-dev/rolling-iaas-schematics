FROM python:3.10.10-slim-bullseye

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV IBMCLOUD_API_KEY $IBMCLOUD_API_KEY
ENV WORKSPACE_ID $WORKSPACE_ID

CMD [ "python", "./main.py" ]