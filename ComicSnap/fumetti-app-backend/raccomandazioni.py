import sqlite3
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
import os
from collections import defaultdict

class SistemaRaccomandazione:
    """
    Un sistema di raccomandazione per fumetti che utilizza sia il filtraggio collaborativo
    che le preferenze esplicite degli utenti per generare suggerimenti personalizzati.
    """
    def __init__(self, db_connection: sqlite3.Connection):
        """
        Inizializza il sistema di raccomandazione.
        
        Args:
            db_connection: Connessione al database SQLite contenente i dati degli utenti
        """
        self.conn = db_connection
        self.api_key = os.getenv('COMICVINE_API_KEY')  # Recupera la chiave API dalle variabili d'ambiente
        self.base_url = "https://comicvine.gamespot.com/api/search/"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def ottieni_preferenze_utente(self, utente_id: int) -> Dict[str, float]:
        """
        Recupera le preferenze esplicite dell'utente dal database.
        
        Args:
            utente_id: ID dell'utente
        Returns:
            Dizionario con comic_id come chiave e peso della preferenza come valore
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT comic_id, peso
            FROM preferenze_utente
            WHERE utente_id = ?
        ''', (utente_id,))
        return dict(cursor.fetchall())

    def ottieni_editori_preferiti(self, utente_id: int) -> List[Tuple[str, float]]:
        """
        Identifica i 3 editori preferiti dell'utente basandosi sui rating medi.
        
        Args:
            utente_id: ID dell'utente
        Returns:
            Lista di tuple (editore, rating_medio) ordinate per rating decrescente
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT f.editore, AVG(fl.rating) as rating_medio
            FROM fumetti f
            JOIN fumetti_letti fl ON f.id = fl.comic_id
            WHERE fl.utente_id = ? AND f.editore IS NOT NULL
            GROUP BY f.editore
            ORDER BY rating_medio DESC
            LIMIT 3
        ''', (utente_id,))
        return cursor.fetchall()

    def ottieni_fumetti_letti(self, utente_id: int) -> List[str]:
        """
        Recupera l'elenco dei fumetti già letti dall'utente.
        
        Args:
            utente_id: ID dell'utente
        Returns:
            Lista di ID dei fumetti letti
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT comic_id FROM fumetti_letti WHERE utente_id = ?', (utente_id,))
        return [str(row[0]) for row in cursor.fetchall()]

    def calcola_similarita_utenti(self, utente_id: int) -> Dict[int, float]:
        """
        Calcola la similarità coseno tra l'utente dato e tutti gli altri utenti
        basandosi sui rating dei fumetti in comune.
        
        Args:
            utente_id: ID dell'utente
        Returns:
            Dizionario con user_id come chiave e similarità coseno come valore
        """
        cursor = self.conn.cursor()
        # Ottiene i rating dell'utente target
        cursor.execute('''
            SELECT comic_id, rating 
            FROM fumetti_letti 
            WHERE utente_id = ?
        ''', (utente_id,))
        ratings_utente = dict(cursor.fetchall())
        
        # Ottiene la lista degli altri utenti
        cursor.execute('''
            SELECT DISTINCT utente_id 
            FROM fumetti_letti 
            WHERE utente_id != ?
        ''', (utente_id,))
        altri_utenti = [row[0] for row in cursor.fetchall()]
        
        similarita = {}
        for altro_utente in altri_utenti:
            # Ottiene i rating dell'altro utente
            cursor.execute('''
                SELECT comic_id, rating 
                FROM fumetti_letti 
                WHERE utente_id = ?
            ''', (altro_utente,))
            ratings_altro = dict(cursor.fetchall())
            
            # Calcola similarità coseno solo se ci sono fumetti in comune
            fumetti_comuni = set(ratings_utente.keys()) & set(ratings_altro.keys())
            if fumetti_comuni:
                numeratore = sum(ratings_utente[f] * ratings_altro[f] for f in fumetti_comuni)
                denominatore = (sum(ratings_utente[f]**2 for f in fumetti_comuni) ** 0.5) * \
                             (sum(ratings_altro[f]**2 for f in fumetti_comuni) ** 0.5)
                similarita[altro_utente] = numeratore / denominatore if denominatore > 0 else 0
        
        return similarita

    def ottieni_raccomandazioni_collaborative(self, utente_id: int, similarita_utenti: Dict[int, float]) -> Dict[str, float]:
        """
        Genera raccomandazioni usando il filtraggio collaborativo basato su utenti.
        Considera solo i fumetti con rating >= 4.
        
        Args:
            utente_id: ID dell'utente
            similarita_utenti: Dizionario delle similarità con altri utenti
        Returns:
            Dizionario con comic_id come chiave e score di raccomandazione come valore
        """
        cursor = self.conn.cursor()
        fumetti_raccomandati = defaultdict(float)
        
        for altro_utente, sim in similarita_utenti.items():
            cursor.execute('''
                SELECT comic_id, rating 
                FROM fumetti_letti 
                WHERE utente_id = ? AND rating >= 4
            ''', (altro_utente,))
            for comic_id, rating in cursor.fetchall():
                fumetti_raccomandati[comic_id] += sim * rating
        
        return fumetti_raccomandati

    def genera_raccomandazioni(self, utente_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Genera raccomandazioni finali combinando:
        - Preferenze esplicite dell'utente
        - Editori preferiti
        - Raccomandazioni collaborative
        - Dati da API esterna (ComicVine)
        
        Args:
            utente_id: ID dell'utente
            limit: Numero massimo di raccomandazioni da restituire
        Returns:
            Lista di dizionari contenenti le informazioni dei fumetti raccomandati
        """
        try:
            # Raccolta dati utente
            preferenze = self.ottieni_preferenze_utente(utente_id)
            editori_preferiti = self.ottieni_editori_preferiti(utente_id)
            fumetti_letti = self.ottieni_fumetti_letti(utente_id)
            
            # Calcolo raccomandazioni collaborative
            similarita_utenti = self.calcola_similarita_utenti(utente_id)
            fumetti_raccomandati = self.ottieni_raccomandazioni_collaborative(utente_id, similarita_utenti)
            
            # Preparazione query API usando gli editori preferiti
            query = ' OR '.join(editore for editore, _ in editori_preferiti) if editori_preferiti else 'comics'
            params = {
                'api_key': self.api_key,
                'query': query,
                'resources': 'volume',
                'format': 'xml',
                'limit': 100
            }
            
            # Chiamata API
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
            
            raccomandazioni = []
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                volumes = root.findall(".//volume")
                
                # Elaborazione risultati API
                for volume in volumes:
                    volume_id = volume.find(".//id").text
                    titolo = volume.find(".//name").text
                    editore = volume.find(".//publisher/name").text
                    
                    # Filtra fumetti già letti e titoli non validi
                    if (volume_id not in fumetti_letti and 
                        titolo and titolo.strip() and titolo.lower() != "null"):
                        
                        # Calcolo score finale combinando diversi fattori
                        score = 0
                        # Bonus per editori preferiti
                        if editore:
                            for ed_pref, rating_medio in editori_preferiti:
                                if editore == ed_pref:
                                    score += rating_medio
                        
                        # Aggiunge score da raccomandazioni collaborative
                        if volume_id in fumetti_raccomandati:
                            score += fumetti_raccomandati[volume_id]
                        
                        # Moltiplica per preferenze esplicite se presenti
                        if volume_id in preferenze:
                            score *= (1 + preferenze[volume_id])
                        
                        # Creazione oggetto raccomandazione
                        raccomandazioni.append({
                            'id': volume_id,
                            'titolo': titolo,
                            'copertina': volume.find(".//image/small_url").text,
                            'editore': editore,
                            'anno': volume.find(".//start_year").text if volume.find(".//start_year") is not None else "N/D",
                            'score': round(score, 2)
                        })
                
                # Ordinamento finale e limite risultati
                raccomandazioni.sort(key=lambda x: x['score'], reverse=True)
                raccomandazioni = raccomandazioni[:limit]
            
            return raccomandazioni
            
        except Exception as e:
            print(f"Errore dettagliato: {e}")
            return []