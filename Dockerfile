FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Pre-warm the embedding model into the image so container start isn't
# blocked on a first-request model download.
RUN python -c "from app.vectorstore import build_vectorstore; from app.data_gen import generate_dataset; build_vectorstore(generate_dataset())"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
