FROM python:3.11.5-slim

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-multipart

COPY app.py ./
COPY schemas.py ./
COPY faiss_agent.py ./
COPY mypdf.py ./

# If any are folders, use:
# COPY schemas/ ./schemas/
# COPY faiss_agent/ ./faiss_agent/
# COPY mypdf/ ./mypdf/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]