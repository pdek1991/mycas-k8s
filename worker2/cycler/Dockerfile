FROM python:3.8.19
#comment
WORKDIR /app/cycler

COPY requirements.txt .
RUN pip install --no-cache-dir -r /app/cycler/requirements.txt

VOLUME ["/app/cycler"]

COPY . .
CMD ["python", "cycler.py"]
