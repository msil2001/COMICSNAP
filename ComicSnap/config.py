import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

class Config:
    # Chiavi di sicurezza
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key-never-use-in-production')
    COMICVINE_API_KEY = os.getenv('COMICVINE_API_KEY')
    
    # Configurazione Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'comicsnap.db')
    
    # Altri parametri
    MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', 100))
    TOKEN_EXPIRY_HOURS = int(os.getenv('TOKEN_EXPIRY_HOURS', 24))
