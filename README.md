
# ComicSnap

## About the project

ComicSnap is an application for manga and comic book lovers, created to help users choose their next reads through our recommendation system and to allow them to take into account the comics they have already read, giving them the chance to assign a rating from 1 to 5 stars and a weight that can influence the recommendations.

## Built with

ComicSnap was built using several technologies: HTML, CSS and JavaScript for the front-end development, Python for the back-end development, and the Flask microframework to implement the server; Comic Vine was also used as an API to draw from for comics.

<!-- SYSTEM REQUIREMENTS -->
## System Requirements

> [!IMPORTANT]
> To correctly execute the behavior of this PWA you must have the following prerequisites pre-installed on your system:
> - Python 3.x
> - pip (Python Package Installer) - latest version
> - SQlite Database - latest version (https://www.sqlite.org/)

<!-- SETTING UP VENV -->
## Setting Up the Virtual Environment

1. Ensure you have Python correctly installed (and at the latest version) on your system.

2. Open the terminal:
    - On Windows: Use Command Prompt.
    - On macOS and Linux: Use the system terminal.
    
3. Navigate to your project directory if necessary.

4. Create a virtual environment by running the following command:
    ```bash
    python -m venv venv
    ```
5. Then enter in the virtual environment
    - For MacOS or Linux systems:
        ```bash
        source venv/bin/activate
        ```
    - For Windows:
        ```bash
        venv\Scripts\activate
        ```
		> **Warning**  
		> Some versions of Windows may restrict the execution of scripts such as `.bat` from the terminal for security reasons. Make sure you have this option ***disabled***. You may find this option under the name *UAC* (User Access Control).
6. Install dependencies:
    ```bash
    pip install --upgrade -r requirements.txt
    ```
    Then, to update any modules:
    ```bash
    pip install --upgrade flask werkzeug PyJWT requests python-dotenv flask-cors sqlite3 xml.etree.ElementTree uuid jwt functools datetime timezone
    ```
7. Get your ComicVine API key from: https://comicvine.gamespot.com/api/
8. Create your own .env file and put your keys following this template:
	```txt
 	# Chiavi di sicurezza
	SECRET_KEY=your_secret_key
	COMICVINE_API_KEY=yout_comicvine_api_key
	
	# Configurazione Database
	DATABASE_PATH=comicsnap.db
	
	# Altri parametri di configurazione
	MAX_SEARCH_RESULTS=100
	TOKEN_EXPIRY_HOURS=24
	```
 9. Include your .env file to your .gitignore
    ```bash
    echo ".env" >> .gitignore
    ```

## How to run

You can run the application by typing:

```python app.py```

ComicSnap should now be accessible at http://127.0.0.1:5000 in your web-browser.

## License

This application was distributed under the Apache 2.0 License. See [LICENSE](LICENSE) for more details.

## Contacts

Castrese Luca Lucciola - castreseluca.lucciola001@studenti.uniparthenope.it

Mauro Silvestro - mauro.silvestro001@studenti.uniparthenope.it
