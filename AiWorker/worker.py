import os
import json
import redis
import psycopg2
import time
import google.generativeai as genai

REDIS_HOST = os.getenv("REDIS_HOST", "redis_queue")
DB_HOST = os.getenv("DB_HOST", "postgres_db")
DB_NAME = os.getenv("DB_NAME", "bugtracker")
DB_USER = os.getenv("DB_USER", "buguser")
DB_PASS = os.getenv("DB_PASS", "bugpassword")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 1. LISTOWANIE MODELI (Pomocne przy debugowaniu)
    print("AI Worker: Sprawdzam dostępne modele...", flush=True)
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"AI Worker: Dostępne modele: {available_models}", flush=True)
        
        # Wybieramy najlepszy dostępny model
        if 'models/gemini-2.0-flash-lite' in available_models:
            model_name = 'gemini-2.0-flash-lite'
        elif 'models/gemini-1.5-pro' in available_models:
            model_name = 'gemini-1.5-pro'
        else:
            model_name = 'gemini-pro' # Stary, sprawdzony model
            
        print(f"AI Worker: Wybieram model: {model_name}", flush=True)
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"AI Worker: Błąd podczas listowania modeli: {e}", flush=True)
        # Fallback na sztywno, jeśli listowanie zawiedzie
        model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("UWAGA: Brak klucza GEMINI_API_KEY!", flush=True)
    model = None

def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

def analyze_with_gemini(error_msg, logs):
    if not model:
        return "Brak klucza API - analiza niemożliwa."

    prompt = f"""
    Jesteś ekspertem od debugowania aplikacji (Java/C#/Web).
    Przeanalizuj poniższy błąd i logi.
    
    BŁĄD: {error_msg}
    
    OSTATNIE LOGI (Context):
    {json.dumps(logs, indent=2)}
    
    Twoim zadaniem jest znaleźć przyczynę.
    Odpowiedz WYŁĄCZNIE czystym tekstem (bez markdown), krótko i zwięźle w formacie:
    
    PRZYCZYNA: <jedno zdanie co poszło nie tak>
    ROZWIĄZANIE: <konkretna rada jak to naprawić w kodzie>
    PRIORYTET: <LOW / MEDIUM / HIGH / CRITICAL>
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Błąd Gemini API: {str(e)}"

def main():
    print("AI Worker (Gemini): Startuje...", flush=True)
    
    time.sleep(5)
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bug_reports (
                id SERIAL PRIMARY KEY,
                error_message TEXT,
                ai_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        print("AI Worker: Baza danych gotowa.", flush=True)
    except Exception as e:
        print(f"AI Worker: Błąd połączenia z bazą: {e}", flush=True)

    print("AI Worker: Nasłuchuję kolejki 'raw_bugs_queue'...", flush=True)

    while True:
        queue, message = r.blpop("raw_bugs_queue")
        
        try:
            print("AI Worker: Pobrano błąd! Wysyłam do Gemini...", flush=True)
            data = json.loads(message)
            
            error_msg = data.get("errorMessage", "Nieznany błąd")
            logs = data.get("breadcrumbs", [])

            analysis = analyze_with_gemini(error_msg, logs)


            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO bug_reports (error_message, ai_analysis) VALUES (%s, %s)",
                (error_msg, analysis)
            )
            conn.commit()
            conn.close()
            
            print("AI Worker: Analiza zakończona i zapisana!", flush=True)
            
        except Exception as e:
            print(f"AI Worker: Błąd przetwarzania: {e}", flush=True)

if __name__ == "__main__":
    main()