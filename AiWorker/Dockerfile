# Używamy lekkiej wersji Pythona
FROM python:3.9-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Najpierw kopiujemy tylko plik z zależnościami
# Dzięki temu Docker nie będzie instalował bibliotek od nowa przy każdej zmianie w kodzie
COPY requirements.txt .

# Instalujemy biblioteki (Redis, Postgres, Google Gemini)
RUN pip install --no-cache-dir -r requirements.txt

# Dopiero teraz kopiujemy resztę kodu (skrypt worker.py)
COPY . .

# Uruchamiamy skrypt z flagą "-u" (unbuffered)
# To sprawia, że print() w Pythonie od razu trafia do logów Dockera
CMD ["python", "-u", "worker.py"]