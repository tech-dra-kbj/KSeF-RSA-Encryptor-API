# 🔐 KSeF RSA Encryptor API

REST API do szyfrowania danych (np. kluczy AES lub tokenów) zgodnie z wymogami **KSeF**  
z użyciem algorytmu **RSAES-OAEP (MGF1 + SHA-256)**.

Serwis oparty o **Flask + Gunicorn**, z dokumentacją w **Swagger UI**  
i pełną obsługą **CORS** (możliwość testowania bezpośrednio w przeglądarce).


- [Funkcje](#funkcje)
- [Struktura projektu](#-struktura-projektu)
- [Wymagania](#wymagania)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Przykładowe użycie API](#przykładowe-użycie-api)
- [Uruchomienie jako serwis w Linux (systemd)](#uruchomienie-jako-serwis-w-linux-systemd)
- [Uruchomienie jako serwis w Linux (systemd) — wariant z Gunicorn](#uruchomienie-jako-serwis-w-linux-systemd--wariant-z-gunicorn)
- [Uruchomienie w Dockerze](#-uruchomienie-w-dockerze)
- [Health-check (dla K8s / monitoringów)](#health-check-dla-k8s--monitoringów)
- [Definicja OpenAPI](#definicja-openapi)
- [Testy manualne](#testy-manualne)
- [Zależności](#zależności)


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

## Uruchomienie jako serwis w Linux (systemd)

Poniższy przykład pokazuje, jak uruchomić aplikację **KSeF RSA Encryptor API** jako usługę systemową (`systemd`) w systemie Linux.  
Usługa będzie automatycznie uruchamiana po restarcie systemu i logować dane do `/var/log`.

---

### Utwórz plik jednostki systemowej

Utwórz plik:
```bash
sudo nano /etc/systemd/system/ksef-encryptor.service
```

Wklej poniższą konfigurację (dostosuj ścieżki i użytkownika):

```ini
[Unit]
Description=KSeF RSA Encryptor Flask Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/KSeF-RSA-Encryptor-API
Environment="PORT=5000"
ExecStart=/home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/python3 /home/ubuntu/KSeF-RSA-Encryptor-API/encrypt_service.py
Restart=always
StandardOutput=append:/var/log/encrypt_service.log
StandardError=append:/var/log/encrypt_service.err

[Install]
WantedBy=multi-user.target
```

**Ważne parametry:**
- `WorkingDirectory` — ścieżka do katalogu projektu  
- `ExecStart` — ścieżka do interpretera Pythona z wirtualnego środowiska  
- `Environment="PORT=5000"` — tutaj możesz zmienić port, na którym działa aplikacja  
  (np. `Environment="PORT=8080"`)  

---

### Zastosowanie zmian i uruchomienie usługi

```bash
sudo systemctl daemon-reload
sudo systemctl enable ksef-encryptor.service
sudo systemctl start ksef-encryptor.service
```

---

### Sprawdzenie statusu serwisu

```bash
sudo systemctl status ksef-encryptor.service
```

Przykładowy wynik:
```
● ksef-encryptor.service - KSeF RSA Encryptor Flask Service
   Loaded: loaded (/etc/systemd/system/ksef-encryptor.service; enabled)
   Active: active (running) since Fri 2025-10-17 09:41:13 CEST; 10s ago
 Main PID: 21345 (python3)
    Tasks: 1 (limit: 4915)
   Memory: 52.3M
   CGroup: /system.slice/ksef-encryptor.service
           └─21345 /home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/python3 /home/ubuntu/KSeF-RSA-Encryptor-API/encrypt_service.py
```

---

### Logi aplikacji

```bash
sudo tail -f /var/log/encrypt_service.log
sudo tail -f /var/log/encrypt_service.err
```

---

### Restart / zatrzymanie usługi

```bash
sudo systemctl restart ksef-encryptor.service
sudo systemctl stop ksef-encryptor.service
```

---

### Po starcie systemu

Usługa uruchomi się automatycznie i będzie dostępna pod adresem:
```
http://localhost:<PORT>
```

Przykład:
```
http://localhost:5000
```

---

## Uruchomienie jako serwis w Linux (systemd) — wariant z Gunicorn

Wersja z **wieloma workerami i wątkami**, zalecana do środowisk produkcyjnych.  
Gunicorn automatycznie zarządza procesami workerów i zapewnia większą stabilność niż natywny serwer Flask.

---

### Utwórz plik jednostki systemowej

Utwórz plik:
```bash
sudo nano /etc/systemd/system/ksef-encryptor.service
```

Wklej poniższą konfigurację (dostosuj ścieżki i użytkownika):

```ini
[Unit]
Description=KSeF RSA Encryptor Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/KSeF-RSA-Encryptor-API
Environment="PORT=5000"
Environment="WORKERS=3"
Environment="THREADS=2"
ExecStart=/home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/gunicorn --workers ${WORKERS} --threads ${THREADS} --bind 0.0.0.0:${PORT} encrypt_service:app
Restart=always
RestartSec=5
StandardOutput=append:/var/log/encrypt_service.log
StandardError=append:/var/log/encrypt_service.err

[Install]
WantedBy=multi-user.target
```

**Ważne parametry:**
- `Environment="PORT=5000"` — port HTTP (zmień np. na 8080)
- `Environment="WORKERS=3"` — liczba procesów (workerów)
- `Environment="THREADS=2"` — liczba wątków per worker
- `WorkingDirectory` — katalog projektu
- `ExecStart` — ścieżka do Gunicorna z wirtualnego środowiska

---

### Wczytanie zmian i uruchomienie usługi

```bash
sudo systemctl daemon-reload
sudo systemctl enable ksef-encryptor.service
sudo systemctl start ksef-encryptor.service
```

---

### Sprawdzenie statusu

```bash
sudo systemctl status ksef-encryptor.service
```

Przykładowy wynik:
```
● ksef-encryptor.service - KSeF RSA Encryptor Gunicorn Service
   Loaded: loaded (/etc/systemd/system/ksef-encryptor.service; enabled)
   Active: active (running) since Fri 2025-10-17 09:41:13 CEST; 10s ago
 Main PID: 21345 (gunicorn)
    Tasks: 4 (limit: 4915)
   CGroup: /system.slice/ksef-encryptor.service
           ├─21345 /home/ubuntu/KSeF-RSA-Encryptor-API/.venv/bin/gunicorn --workers 3 --threads 2 --bind 0.0.0.0:5000 encrypt_service:app
           ├─21347 gunicorn: worker [1]
           ├─21348 gunicorn: worker [2]
           └─21349 gunicorn: worker [3]
```

---

### Logi aplikacji

```bash
sudo tail -f /var/log/encrypt_service.log
sudo tail -f /var/log/encrypt_service.err
```

---

### Restart / zatrzymanie

```bash
sudo systemctl restart ksef-encryptor.service
sudo systemctl stop ksef-encryptor.service
```

---

### Po starcie systemu

Usługa uruchomi się automatycznie i będzie dostępna pod adresem:
```
http://localhost:<PORT>
```

Przykład:
```
http://localhost:5000
```

---

**Rekomendacja:**  
W środowiskach produkcyjnych zaleca się używanie tego wariantu z Gunicornem zamiast natywnego serwera Flask.


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
