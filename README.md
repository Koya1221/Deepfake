# Flask Deepfake Demo

## Setup (local)
1. python -m venv venv
2. source venv/bin/activate  (Windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. flask --app app.py init-db
5. python app.py
6. Open http://127.0.0.1:5000

## Use PostgreSQL
Set env var:
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
Then run `flask --app app.py init-db`

## Docker
docker build -t deepfake-demo .
docker run -p 5000:5000 deepfake-demo
