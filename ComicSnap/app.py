from flask import Flask, jsonify, request, g, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from config import Config
from raccomandazioni import SistemaRaccomandazione
from datetime import datetime, timezone
import jwt
import functools
import requests
import uuid
import xml.etree.ElementTree as ET

# Inizializzazione dell'app Flask
app = Flask(__name__)
app.config.from_object(Config)
 
# Middleware per verificare il token JWT
# Si usa per far si che le route protette siano accessibili solo con un token valido
def richiedi_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Token mancante'}), 401
            
        try:
            # Estrae il token dalla stringa 'Bearer <token>'
            token = token.split()[1]  
            # Decodifica e verifica il token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Verifica scadenza token
            exp_timestamp = data.get('exp')
            if not exp_timestamp:
                return jsonify({'message': 'Token non valido: manca scadenza'}), 401
                
            # Confronta il timestamp corrente con la scadenza del token
            current_timestamp = datetime.now(timezone.utc).timestamp()
            if current_timestamp > exp_timestamp:
                return jsonify({'message': 'Token scaduto'}), 401
                
            # Memorizza l'ID utente nel contesto globale di Flask
            g.utente_id = data['utente_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token scaduto'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token non valido'}), 401
            
        return f(*args, **kwargs)
    return decorated

# Funzione helper per la connessione al database SQLite
def connetti_db():
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    # Permette l'accesso alle colonne per nome invece che per indice
    conn.row_factory = sqlite3.Row  
    return conn

# Inizializzazione del database
def inizializza_db():
    conn = connetti_db()
    cursor = conn.cursor()
    
    # Creazione delle tabelle con relativi vincoli e relazioni
    cursor.executescript('''
        -- Tabella per gli utenti registrati
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            data_registrazione DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Tabella per memorizzare le preferenze degli utenti sui fumetti
        CREATE TABLE IF NOT EXISTS preferenze_utente (
            id INTEGER PRIMARY KEY,
            utente_id INTEGER,
            comic_id TEXT NOT NULL,
            genere TEXT NOT NULL,
            peso REAL DEFAULT 1.0,
            FOREIGN KEY (utente_id) REFERENCES utenti (id)
        );

        -- Tabella per tracciare i fumetti letti dagli utenti con valutazione
        CREATE TABLE IF NOT EXISTS fumetti_letti (
            id INTEGER PRIMARY KEY,
            utente_id INTEGER,
            comic_id TEXT NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            data_lettura DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (utente_id) REFERENCES utenti (id)
        );
        
        -- Tabella principale dei fumetti con informazioni dettagliate
        CREATE TABLE IF NOT EXISTS fumetti (
            id TEXT PRIMARY KEY,
            titolo TEXT NOT NULL,
            url_copertina TEXT,
            data_aggiunta DATETIME DEFAULT CURRENT_TIMESTAMP,
            editore TEXT,
            anno INTEGER
        );
    ''')
    
    conn.commit()
    conn.close()

# Funzione per cercare fumetti tramite l'API di ComicVine
# Gestisce la paginazione (nonostante max_results sia hardcodato a 100) e il parsing dei risultati XML
def cerca_fumetti(query, genere_preferito=None):
    base_url = "https://comicvine.gamespot.com/api/search/"
    api_key = app.config['COMICVINE_API_KEY']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
    }

    limit = 100
    offset = 0
    all_volumes = []
    max_results = app.config['MAX_SEARCH_RESULTS']

    while len(all_volumes) < max_results:
        params = {
            'api_key': api_key,
            'query': query,
            'resources': 'volume',
            'format': 'xml',
            'limit': limit,
            'offset': offset
        }

        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            try:
                root = ET.fromstring(response.text)
                volumes = root.findall(".//volume")

                for volume in volumes:
                    # Verifica subito se il nome è presente e valido
                    name_element = volume.find(".//name")
                    if name_element is None or not name_element.text or name_element.text.strip() == "":
                        continue

                    volume_id = volume.get('id') or str(uuid.uuid4())
                    
                    # Estrazione degli autori
                    autori = []
                    writers = volume.findall(".//person[@role='writer']/name")
                    for writer in writers:
                        if writer.text and writer.text not in autori:
                            autori.append(writer.text)
                    
                    if not autori:
                        artists = volume.findall(".//person[@role='artist']/name")
                        for artist in artists:
                            if artist.text and artist.text not in autori:
                                autori.append(artist.text)
                    
                    autori_str = ", ".join(autori) if autori else "Autore non specificato"
                    
                    # Estrazione e validazione degli altri campi
                    deck_element = volume.find(".//deck")
                    description = deck_element.text if deck_element is not None else "N/A"
                    
                    year_element = volume.find(".//start_year")
                    year = year_element.text if year_element is not None else "N/A"
                    
                    publisher_element = volume.find(".//publisher/name")
                    publisher = publisher_element.text if publisher_element is not None else "N/A"
                    
                    image_element = volume.find(".//image/small_url")
                    image_url = image_element.text if image_element is not None else "N/A"

                    volume_data = {
                        "id": volume_id,
                        "Nome del volume": name_element.text.strip(),
                        "Descrizione": description,
                        "Anno di pubblicazione": year,
                        "Editore": publisher,
                        "Immagine di copertina": image_url,
                        "Autore": autori_str
                    }

                    all_volumes.append(volume_data)

                    if len(all_volumes) >= max_results:
                        break

                if len(volumes) < limit:
                    break

                offset += limit

            except ET.ParseError as e:
                print(f"Errore di parsing XML: {e}")
                break
        else:
            print(f"Errore nella richiesta API: {response.status_code}")
            break

    return all_volumes

# Route principale che serve la pagina index
@app.route('/')
def home():
    return render_template('index.html')

# Route per la ricerca dei fumetti
@app.route('/search', methods=['GET'])
def search_fumetti():
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Termine di ricerca mancante'}), 400
    
    results = cerca_fumetti(query)
    return jsonify(results)

# Route per la pagina dei risultati di ricerca
@app.route('/risultati_ricerca.html')
def risultati_ricerca():
    return render_template('risultati.html')

# Route per aggiungere un fumetto alla lista dei letti
@app.route('/aggiungi_fumetto_letto', methods=['POST'])
@richiedi_auth
def aggiungi_fumetto_letto():
    data = request.json
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400
    
    # Estrazione e validazione dei dati del fumetto
    comic_id = data.get('comic_id', '').strip()
    titolo = data.get('titolo', '').strip()
    autore = data.get('autore', 'Autore non specificato').strip()
    url_copertina = data.get('url_copertina', '').strip() or '/static/comic-placeholder.png'
    rating = data.get('rating')
    editore = data.get('editore', 'Non specificato').strip()
    anno = data.get('anno', 'N/D').strip()
    
    if not comic_id or not titolo:
        return jsonify({"error": "Comic ID e Titolo sono richiesti"}), 400
    
    try:
        conn = connetti_db()
        cursor = conn.cursor()
        
        # Verifica se il fumetto è già stato aggiunto dall'utente
        cursor.execute("SELECT 1 FROM fumetti_letti WHERE utente_id = ? AND comic_id = ?", 
                      (g.utente_id, comic_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Hai già aggiunto questo fumetto"}), 409
        
        # Inserisce o aggiorna i dati del fumetto nella tabella fumetti
        cursor.execute("""
            INSERT OR IGNORE INTO fumetti (id, titolo, autore, url_copertina, editore, anno) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (comic_id, titolo, autore, url_copertina, editore, anno))
        
        # Registra la lettura dell'utente
        cursor.execute("""
            INSERT INTO fumetti_letti (utente_id, comic_id, rating) 
            VALUES (?, ?, ?)
        """, (g.utente_id, comic_id, rating))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Fumetto aggiunto con successo"}), 200
    
    except sqlite3.Error as e:
        return jsonify({"error": "Errore interno del server"}), 500

# Route per verificare se un fumetto è già stato letto dall'utente
@app.route('/aggiungi_fumetto_letto/<comic_id>', methods=['GET'])
@richiedi_auth
def verifica_fumetto_letto(comic_id):
    try:
        conn = connetti_db()
        cursor = conn.cursor()
        # Verifica presenza del fumetto nella lista dei letti
        cursor.execute("SELECT 1 FROM fumetti_letti WHERE utente_id = ? AND comic_id = ?", 
                      (g.utente_id, comic_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Fumetto già aggiunto"}), 409
        conn.close()
        return jsonify({"message": "Fumetto non presente"}), 200
    except sqlite3.Error:
        return jsonify({"error": "Errore interno del server"}), 500

# Route per ottenere la lista dei fumetti letti dall'utente
@app.route('/fumetti_letti', methods=['GET'])
@richiedi_auth
def get_fumetti_letti():
    try:
        conn = connetti_db()
        cursor = conn.cursor()
        
        # Query per recuperare i dettagli dei fumetti letti
        cursor.execute("""
            SELECT f.id, f.titolo, f.autore, f.url_copertina, f.anno, f.editore
            FROM fumetti_letti fl
            JOIN fumetti f ON fl.comic_id = f.id
            WHERE fl.utente_id = ?
        """, (g.utente_id,))
        
        fumetti = cursor.fetchall()
        conn.close()
        
        # Formatta i risultati per la risposta JSON
        fumetti_list = [
            {
                "id": fumetto['id'], 
                "titolo": fumetto['titolo'], 
                "autore": fumetto['autore'],
                "url_copertina": fumetto['url_copertina'] or '/static/comic-placeholder.png',
                "anno": fumetto['anno'],
                "editore": fumetto['editore']
            } for fumetto in fumetti
        ]
        
        return jsonify(fumetti_list), 200
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    

# Route per aggiungere un fumetto ai preferiti
@app.route('/aggiungi_preferito', methods=['POST'])
@richiedi_auth
def aggiungi_preferito():
    data = request.json
    if not data:
        return jsonify({"error": "Nessun dato ricevuto"}), 400
    
    comic_id = data.get('comic_id')
    peso = data.get('peso')
    
    try:
        conn = connetti_db()
        cursor = conn.cursor()
        
        # Verifica se il fumetto è già nei preferiti dell'utente
        cursor.execute("""
            SELECT id FROM preferenze_utente 
            WHERE utente_id = ? AND comic_id = ?
        """, (g.utente_id, comic_id))
        
        if cursor.fetchone():
            return jsonify({"error": "Fumetto già nei preferiti"}), 400
        
        # Inserisce il nuovo fumetto preferito con peso personalizzato    
        cursor.execute("""
            INSERT INTO preferenze_utente (utente_id, comic_id, genere, peso)
            VALUES (?, ?, 'non_specificato', ?)
        """, (g.utente_id, comic_id, peso))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Preferenza aggiunta con successo"}), 200
        
    except sqlite3.Error as e:
        return jsonify({"error": "Errore del database"}), 500

# Route per verificare quali fumetti sono nei preferiti dell'utente
@app.route('/check_preferiti', methods=['GET'])
@richiedi_auth
def check_preferiti():
    try:
        conn = connetti_db()
        cursor = conn.cursor()
        
        # Recupera tutti gli ID dei fumetti preferiti dell'utente
        cursor.execute("""
            SELECT DISTINCT comic_id 
            FROM preferenze_utente 
            WHERE utente_id = ?
        """, (g.utente_id,))
        
        preferiti = [row['comic_id'] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(preferiti), 200
    except sqlite3.Error as e:
        return jsonify({"error": "Errore del database"}), 500

# Route per la registrazione di nuovi utenti
@app.route('/registrazione', methods=['POST'])
def registra_utente():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username e password sono richiesti'}), 400
    
    conn = connetti_db()
    cursor = conn.cursor()
    
    try:
        # Hash della password prima del salvataggio
        cursor.execute(
            'INSERT INTO utenti (username, password_hash) VALUES (?, ?)',
            (username, generate_password_hash(password))
        )
        conn.commit()
        
        # Effettua il login automatico dopo la registrazione
        cursor.execute('SELECT * FROM utenti WHERE username = ?', (username,))
        utente = cursor.fetchone()
        
        # Genera token JWT per la sessione
        token = jwt.encode(
            {
                'utente_id': utente['id'],
                'username': username,
                'exp': datetime.now(timezone.utc).timestamp() + 24*60*60  # Scade dopo 24 ore
            },
            app.config['SECRET_KEY']
        )
        return jsonify({'token': token})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username già in uso'}), 400
    finally:
        conn.close()

# Route per il login degli utenti
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = connetti_db()
    cursor = conn.cursor()
    # Verifica le credenziali dell'utente
    cursor.execute('SELECT * FROM utenti WHERE username = ?', (username,))
    utente = cursor.fetchone()
    conn.close()
    
    # Verifica password e genera token se corretta
    if utente and check_password_hash(utente['password_hash'], password):
        token = jwt.encode(
            {
                'utente_id': utente['id'],
                'username': username,
                'exp': datetime.utcnow().timestamp() + (app.config['TOKEN_EXPIRY_HOURS'] * 3600) # Scade dopo 24 ore
            },
            app.config['SECRET_KEY']
        )
        return jsonify({'token': token})
    
    return jsonify({'error': 'Credenziali non valide'}), 401

# Route per il logout
@app.route('/logout', methods=['POST'])
def logout():
    # Nota: il logout è gestito lato client rimuovendo il token
    return jsonify({'message': 'Logout effettuato con successo'}), 200


# Routes per le varie pagine dell'applicazione
@app.route('/raccolta')
def raccolta():
    return render_template('raccolta.html')

@app.route('/logreg')
def logreg():
    return render_template('LogReg.html')

# Route per le raccomandazioni con supporto sia JSON che HTML
@app.route('/raccomandazioni', methods=['GET'])
def ottieni_raccomandazioni():
    # Gestisce richieste API (JSON) e pagina web (HTML)
    if request.headers.get('Accept') == 'application/json':
        return richiedi_auth(lambda: _get_raccomandazioni())()
    return render_template('raccomandazioni.html')

# Funzione helper per generare raccomandazioni
def _get_raccomandazioni():
    conn = connetti_db()
    try:
        # Utilizza il sistema di raccomandazione per generare suggerimenti
        sistema_raccomandazione = SistemaRaccomandazione(conn)
        raccomandazioni = sistema_raccomandazione.genera_raccomandazioni(g.utente_id)
        return jsonify(raccomandazioni)
    except Exception as e:
        print(f"Errore: {e}")
        return jsonify({'error': 'Errore nella generazione delle raccomandazioni'}), 500
    finally:
        conn.close()

# Route per la pagina delle raccomandazioni
@app.route('/raccomandazioni.html')
@richiedi_auth
def raccomandazioni_page():
    return render_template('raccomandazioni.html')

# Route per aggiungere un autore ai preferiti
@app.route('/autori-preferiti', methods=['POST'])
@richiedi_auth
def aggiungi_autore_preferito():
    data = request.json
    autore = data.get('autore')
    
    if not autore:
        return jsonify({'error': 'Autore richiesto'}), 400
    
    conn = connetti_db()
    cursor = conn.cursor()
    
    # Aggiunge l'autore ai preferiti dell'utente
    cursor.execute(
        'INSERT INTO autori_preferiti (utente_id, autore) VALUES (?, ?)',
        (g.utente_id, autore)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Autore preferito aggiunto'}), 201

# Route per registrare i fumetti letti con valutazione
@app.route('/fumetti-letti', methods=['POST'])
@richiedi_auth
def registra_lettura():
    data = request.json
    comic_id = data.get('comic_id')
    rating = data.get('rating')
    
    # Validazione dei dati
    if not comic_id or not rating:
        return jsonify({'error': 'Comic ID e rating sono richiesti'}), 400
    
    if not 1 <= rating <= 5:
        return jsonify({'error': 'Il rating deve essere tra 1 e 5'}), 400
    
    conn = connetti_db()
    cursor = conn.cursor()
    
    # Registra la lettura con la valutazione
    cursor.execute('''
        INSERT INTO fumetti_letti (utente_id, comic_id, rating)
        VALUES (?, ?, ?)
    ''', (g.utente_id, comic_id, rating))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Lettura registrata con successo'})

# Avvio dell'applicazione in modalità debug
if __name__ == '__main__':
    inizializza_db()  # Inizializza il database all'avvio
    app.run(debug=True)
