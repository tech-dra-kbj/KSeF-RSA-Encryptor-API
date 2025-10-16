# 🔐 KSeF RSA Encryptor API

REST API do szyfrowania danych (np. kluczy AES lub tokenów) zgodnie z wymogami **KSeF**  
z użyciem algorytmu **RSAES-OAEP (MGF1 + SHA-256)**.

Serwis oparty o **Flask + Gunicorn**, z dokumentacją w **Swagger UI**  
i pełną obsługą **CORS** (możliwość testowania bezpośrednio w przeglądarce).

---

## Funkcje

-  Szyfrowanie danych RSAES-OAEP (MGF1 + SHA-256)
-  Dokumentacja OpenAPI (Swagger UI)
-  Health-check endpoint (`/health`)
-  Uruchamianie jako kontener Docker (z Gunicornem)
-  Obsługa CORS – działa w Swagger UI i frontendach JS
-  Definicja API w zewnętrznym pliku `openapi.yaml`

---

##  Struktura projektu

```
.
├── encrypt_service.py      # Główny kod aplikacji Flask
├── openapi.yaml            # Definicja API (OpenAPI / Swagger)
├── requirements.txt        # Zależności Pythona
└── Dockerfile              # Definicja kontenera (Python 3.10 + Gunicorn)
```

---

## Wymagania

- Python **3.10+**
- Pip / venv
- Docker (opcjonalnie)

---

## Uruchomienie lokalne

### Klonowanie repozytorium
```bash
git clone https://github.com/zvgelo/KSeF-RSA-Encryptor-API.git
cd KSeF-RSA-Encryptor-API
```

### Instalacja zależności
```bash
python -m venv venv
source venv/bin/activate  # Linux / macOS
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Uruchomienie serwisu
```bash
python encrypt_service.py
```

Serwis będzie działał pod adresem:
[http://localhost:5000](http://localhost:5000)

Swagger UI dostępny pod:
[http://localhost:5000/apidocs](http://localhost:5000/apidocs)

---

## Przykładowe użycie API

### Endpoint `/encrypt`

**POST** `http://localhost:5000/encrypt`

#### Przykład żądania:
```json
{
  "data_b64": "ZGFuZV9pbnB1dA==",
  "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...",
  "return_b64": true
}
```

#### Przykład odpowiedzi:
```json
{
  "status": "ok",
  "encrypted_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
}
```

### Endpoint `/health`

**GET** `http://localhost:5000/health`

#### Odpowiedź:
```json
{
  "status": "ok",
  "service": "KSeF RSA Encryptor"
}
```

---

## 🐳 Uruchomienie w Dockerze

### Budowa obrazu
```bash
docker build -t ksef-encryptor .
```

### Uruchomienie kontenera
```bash
docker run -p 5000:5000 ksef-encryptor
```

### Dynamiczny port i worker’y Gunicorna
```bash
docker run -e PORT=8080 -e WORKERS=4 -e THREADS=2 -p 8080:8080 ksef-encryptor
```

---

## Health-check (dla K8s / monitoringów)

Użyj prostego endpointu:

```bash
curl http://localhost:5000/health
```

Zwraca:
```json
{ "status": "ok", "service": "KSeF RSA Encryptor" }
```

---

## Definicja OpenAPI

Definicja znajduje się w pliku [`openapi.yaml`](./openapi.yaml).  
Można ją pobrać w formacie JSON:
```bash
curl http://localhost:5000/apispec_1.json -o openapi.json
```

---

## Testy manualne

### Z użyciem `curl`:
```bash
curl -X POST http://localhost:5000/encrypt \
  -H "Content-Type: application/json" \
  -d '{"data_b64": "ZGFuZQ==", "cert_b64": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."}'
```

### W Swagger UI:
Otwórz: [http://localhost:5000/apidocs](http://localhost:5000/apidocs)

---

## Zależności

| Pakiet | Opis |
|--------|------|
| **Flask** | Lekki framework webowy |
| **Flasgger** | Swagger UI dla Flask |
| **Flask-CORS** | Obsługa CORS |
| **Cryptography** | Biblioteka kryptograficzna |
| **Gunicorn** | Produkcyjny serwer WSGI |

---

## Autor

**Grzegorz Szawuła**  

---

## 📄 Licencja

Projekt udostępniony na licencji **MIT**.  
Używaj zgodnie z zasadami bezpieczeństwa swojej organizacji.
