// Attende che il DOM sia completamente caricato prima di eseguire il codice
document.addEventListener('DOMContentLoaded', () => {
  /**
   * Carica e visualizza i fumetti letti dall'utente
   * Gestisce l'autenticazione e la visualizzazione delle card dei fumetti
   */
  const caricaFumettiLetti = () => {
    const token = localStorage.getItem('token');
    const container = document.querySelector('.raccolta__grid');
  
    // Verifica se l'utente è autenticato
    if (!token) {
      if (container) container.innerHTML = '<p>Effettua il login per visualizzare la tua raccolta</p>';
      return;
    }
  
    // Pulisce il container prima di caricare nuovi contenuti
    if (container) container.innerHTML = '';
  
    // Richiesta API per ottenere i fumetti letti
    fetch('/fumetti_letti', {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    })
    .then(response => {
      if (!response.ok) throw new Error('Impossibile caricare i fumetti');
      return response.json();
    })
    .then(fumetti => {
      if (!container) return;
      // Gestisce il caso in cui non ci sono fumetti nella raccolta
      if (fumetti.length === 0) {
        container.innerHTML = '<p>Nessun fumetto aggiunto alla raccolta</p>';
        return;
      }

      // Richiesta API per verificare i fumetti preferiti
      fetch('/check_preferiti', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(response => response.json())
      .then(preferiti => {
        // Itera su ogni fumetto e crea le relative card
        fumetti.forEach(fumetto => {
          const card = document.createElement('div');
          card.classList.add('raccolta__card');
          
          // Verifica se il fumetto è tra i preferiti
          const isPrefered = preferiti.includes(fumetto.id);
          
          // Costruisce il template HTML della card
          card.innerHTML = `
            <div class="card-container">
              <img src="${fumetto.url_copertina || '/static/comic-placeholder.png'}" 
                   alt="${fumetto.titolo}"
                   data-comic-id="${fumetto.id}"
                   class="comic-image"
                   onerror="this.src='/static/comic-placeholder.png'" />
              ${isPrefered ? '<span class="star-indicator">★</span>' : ''}
            </div>
            <h4>${fumetto.titolo}</h4>
            <p>Anno: ${fumetto.anno || 'N/D'}</p>
            <p>Editore: ${fumetto.editore || 'N/D'}</p>
          `;
          
          container.appendChild(card);

          // Aggiunge l'event listener per la valutazione solo se non è già nei preferiti
          if (!isPrefered) {
            const img = card.querySelector('.comic-image');
            img.addEventListener('click', () => {
              const comicId = img.getAttribute('data-comic-id');
              const comicTitle = img.alt;
              
              // Crea il popup per la valutazione
              const popup = document.createElement('div');
              popup.className = 'rating-popup';
              popup.innerHTML = `
                <div class="rating-content">
                  <h3>Valuta "${comicTitle}"</h3>
                  <input type="number" min="0" max="5" step="0.5" class="peso-input" placeholder="Inserisci un peso da 0 a 5">
                  <div class="rating-buttons">
                    <button class="cancel-btn">Annulla</button>
                    <button class="submit-btn" disabled>Conferma</button>
                  </div>
                </div>
              `;
              
              document.body.appendChild(popup);
              
              const pesoInput = popup.querySelector('.peso-input');
              const submitBtn = popup.querySelector('.submit-btn');
              
              // Gestisce la validazione dell'input
              pesoInput.addEventListener('input', () => {
                const peso = parseFloat(pesoInput.value);
                submitBtn.disabled = !(peso >= 0 && peso <= 5);
              });
              
              // Gestisce l'invio della valutazione
              submitBtn.addEventListener('click', () => {
                fetch('/aggiungi_preferito', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                  },
                  body: JSON.stringify({
                    comic_id: comicId,
                    peso: parseFloat(pesoInput.value)
                  })
                })
                .then(response => {
                  if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error) });
                  }
                  return response.json();
                })
                .then(data => {
                  // Aggiunge l'indicatore stella dopo una valutazione positiva
                  const cardContainer = card.querySelector('.card-container');
                  if (!cardContainer.querySelector('.star-indicator')) {
                    const star = document.createElement('span');
                    star.className = 'star-indicator';
                    star.textContent = '★';
                    cardContainer.appendChild(star);
                  }
                  alert('Preferenza aggiunta con successo!');
                  popup.remove();
                })
                .catch(error => {
                  console.error('Errore:', error);
                  alert(error.message || 'Errore nell\'aggiungere la preferenza');
                });
              });
              
              // Gestisce la chiusura del popup
              popup.querySelector('.cancel-btn').addEventListener('click', () => {
                popup.remove();
              });
            });
          }
        });
      });
    })
    .catch(error => {
      console.error('Errore durante il caricamento dei fumetti letti:', error);
      if (container) {
        container.innerHTML = `<p>Errore: ${error.message}</p>`;
      }
    });
  };

  // Inizializza la funzione caricaFumettiLetti solo nella pagina Raccolta
  if (window.location.pathname === '/raccolta') {
    caricaFumettiLetti();
  }



  /**
   * Gestione della funzionalità di ricerca
   */
  const searchIcon = document.querySelector('.ri-search-line');
  const searchDropdown = document.getElementById('search-dropdown');
  const searchInput = document.getElementById('search-input');

  if (searchIcon && searchDropdown && searchInput) {
    // Gestisce l'apertura/chiusura del dropdown di ricerca
    searchIcon.addEventListener('click', () => {
      searchDropdown.classList.toggle('active');
      if (searchDropdown.classList.contains('active')) {
        searchInput.focus();
      }
    });

    // Chiude il dropdown se si clicca fuori dall'area di ricerca
    document.addEventListener('click', (event) => {
      if (!searchDropdown.contains(event.target) && event.target !== searchIcon) {
        searchDropdown.classList.remove('active');
      }
    });

    // Gestisce l'invio della ricerca
    searchInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        const searchTerm = searchInput.value.trim().toLowerCase();
        
        if (searchTerm.length > 0) {
          window.location.href = `/risultati_ricerca.html?q=${encodeURIComponent(searchTerm)}`;
        }
      }
    });
  }

  /**
   * Gestione della navigazione del sito
   */
  const navLinks = document.querySelectorAll('.nav__links .link a');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const destination = link.textContent.toLowerCase().trim();
        switch(destination) {
            case 'home':
                window.location.href = '/';
                break;
            case 'raccolta':
                window.location.href = '/raccolta';
                break;
            case 'quotazioni':
                window.location.href = '/quotazioni';
                break;
            case 'recensioni':
                window.location.href = '/recensioni';
                break;
            default:
                console.log('Pagina non trovata');
        }
    });
  });

  /**
   * Gestione del form di login
   */
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const formData = new FormData(this);
        const username = formData.get('username');
        const password = formData.get('password');

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('token', data.token);
                window.location.href = '/';
            } else {
                alert(data.error || 'Errore durante il login');
            }
        } catch (error) {
            console.error('Errore:', error);
            alert('Impossibile connettersi al server.');
        }
    });
  }

  /**
   * Gestione del form di registrazione
   */
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        const formData = new FormData(this);
        const username = formData.get('username');
        const password = formData.get('password');

        try {
            const response = await fetch('/registrazione', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                localStorage.setItem('token', data.token);
                window.location.href = '/';
            } else {
                alert(data.error || 'Errore durante la registrazione');
            }
        } catch (error) {
            console.error('Errore:', error);
            alert('Impossibile connettersi al server.');
        }
    });
  }

  /**
   * Gestione della visualizzazione dei form di login/registrazione
   */
  const showRegister = document.getElementById("show-register");
  const showLogin = document.getElementById("show-login");
  if (showRegister && showLogin) {
    // Toggle per mostrare il form di registrazione
    showRegister.addEventListener("click", function() {
      const loginForm = document.getElementById("login-form");
      const registerForm = document.getElementById("register-form");
      if (loginForm && registerForm) {
        loginForm.style.display = "none";
        registerForm.style.display = "block";
      }
    });

    // Toggle per mostrare il form di login
    showLogin.addEventListener("click", function() {
      const loginForm = document.getElementById("login-form");
      const registerForm = document.getElementById("register-form");
      if (loginForm && registerForm) {
        registerForm.style.display = "none";
        loginForm.style.display = "block";
      }
    });
  }

  /**
   * Verifica lo stato di autenticazione dell'utente e aggiorna l'UI di conseguenza
   */
  function checkAuthStatus() {
    const token = localStorage.getItem('token');
    const userIcon = document.getElementById('user-auth-icon');
    
    if (token) {
        if (userIcon) {
            userIcon.classList.add('logged-in');
            userIcon.setAttribute('data-auth', 'true');
        }
    } else {
        if (userIcon) {
            userIcon.classList.remove('logged-in');
            userIcon.setAttribute('data-auth', 'false');
        }
    }
  }

  /**
   * Gestisce il click sull'icona utente per login/logout
   */
  function handleUserIconClick() {
    const userIcon = document.getElementById('user-auth-icon');
    const isAuthenticated = userIcon.getAttribute('data-auth') === 'true';

    if (isAuthenticated) {
        logout();
    } else {
        window.location.href = '/logreg';
    }
  }

  /**
   * Gestisce il processo di logout dell'utente
   */
  async function logout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Pulizia dei dati di sessione
            localStorage.removeItem('token');

            const userIcon = document.getElementById('user-auth-icon');
            if (userIcon) {
                userIcon.classList.remove('logged-in');
                userIcon.setAttribute('data-auth', 'false');
            }

            window.location.href = '/';
        } else {
            console.error('Errore durante il logout sul server.');
        }
    } catch (error) {
        console.error('Errore di connessione al server durante il logout:', error);
    }
  }

  // Inizializza gli event listener per l'icona utente
  const userIcon = document.getElementById('user-auth-icon');
  if (userIcon) {
    userIcon.addEventListener('click', handleUserIconClick);
  }

  // Gestisce il pulsante "Scopri" nella header
  const discoverButton = document.querySelector('.header__content .btn');
  if (discoverButton) {
    discoverButton.addEventListener('click', () => {
      const token = localStorage.getItem('token');
      // Reindirizza alla pagina di login se l'utente non è autenticato,
      // altrimenti va alla pagina delle raccomandazioni
      if (!token) {
        window.location.href = '/logreg';
      } else {
        window.location.href = '/raccomandazioni';
      }
    });
  }

  // Verifica lo stato di autenticazione all'avvio dell'applicazione
  checkAuthStatus();
});