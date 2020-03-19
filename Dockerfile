FROM python:3

WORKDIR /hap

COPY requirements.txt ./
RUN pip install --no-cache-dir -r /hap/requirements.txt

CMD [ "python", "/hap/bridge.py" ]