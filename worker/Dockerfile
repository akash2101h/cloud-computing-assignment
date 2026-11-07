FROM python:3.11-slim
WORKDIR /app
COPY worker/requirements.txt worker/requirements.txt
RUN pip install --no-cache-dir -r worker/requirements.txt
COPY worker/worker.py worker/s3util.py worker/teacher_client.py worker/
COPY prompts/teacher_prompt.txt prompts/
ENV PYTHONUNBUFFERED=1
CMD ["python", "worker/worker.py"]
