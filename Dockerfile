# Dùng Python chính thức, nhẹ, có sẵn apt
FROM python:3.10-slim

# Cài các gói hệ thống cần cho opencv và numpy
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dev libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file dự án vào container
COPY . /app

# Cài pip và các thư viện cần thiết
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Port Flask sẽ chạy
EXPOSE 5000

# Chạy app
CMD ["python", "app.py"]
