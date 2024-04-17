FROM python:3.8.19

#comment
WORKDIR /app/stb

COPY requirements.txt .
RUN pip install --no-cache-dir -r /app/stb/requirements.txt

VOLUME ["/app/stb"]

COPY . .

CMD ["python", "stb.py"]

