FROM python:3.11-slim
WORKDIR /app
COPY service/requirements-torch.txt service/requirements.txt ./
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu -r requirements-torch.txt \
 && pip install --no-cache-dir -r requirements.txt
COPY service/app.py .
ENV PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
