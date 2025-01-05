// Attende che il DOM sia completamente caricato prima di eseguire il codice
document.addEventListener('DOMContentLoaded', () => {
    // Recupera il container dove verranno mostrati i risultati della ricerca
    const risultatiContainer = document.getElementById('risultati-ricerca');
    // Estrae i parametri dalla URL
    const searchParams = new URLSearchParams(window.location.search);
    // Ottiene il termine di ricerca dal parametro 'q' nell'URL
    const searchTerm = searchParams.get('q');

    // Procede solo se esiste un termine di ricerca e il container dei risultati
    if (searchTerm && risultatiContainer) {
        // Effettua la chiamata API al backend per la ricerca
        fetch(`/search?q=${encodeURIComponent(searchTerm)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Errore nella ricerca');
                }
                return response.json();
            })
            .then(data => {
                // Pulisce il container dei risultati precedenti
                risultatiContainer.innerHTML = ''; 

                // Se ci sono risultati, li processa
                if (data && data.length > 0) {
                    // Itera su ogni fumetto trovato
                    data.forEach((fumetto, index) => {
                        // Crea una card per ogni fumetto
                        const cardDiv = document.createElement('div');
                        cardDiv.classList.add('raccolta__card');
                        
                        // Genera un ID univoco per il fumetto se non presente
                        const comicId = fumetto.id || `generated_id_${index}`;
                        
               // Costruisce l'HTML della card con i dati del fumetto, usando operatori di fallback per gestire dati mancanti 
                        cardDiv.innerHTML = `
                            <img src="${fumetto["Immagine di copertina"] || fumetto.image?.original_url || 'static/default_cover.jpg'}" 
                                 alt="${fumetto["Nome del volume"] || fumetto.name || 'Fumetto'}"
                                 data-comic-id="${comicId}"
                                 onerror="this.src='static/default_cover.jpg'"
                                 class="comic-image">
                            <h4>${fumetto["Nome del volume"] || fumetto.name || 'Titolo non disponibile'}</h4>
                            <p>Anno: ${fumetto["Anno di pubblicazione"] || fumetto.start_year || 'N/D'}</p>
                            <p>Editore: ${fumetto["Editore"] || fumetto.publisher?.name || 'N/D'}</p>
                        `;
                        risultatiContainer.appendChild(cardDiv);
                    });

                    // Aggiunge gli event listener per le immagini dei fumetti
                    const comicImages = document.querySelectorAll('.comic-image');
                    comicImages.forEach(img => {
                        img.addEventListener('click', async () => {
                            const comicId = img.getAttribute('data-comic-id');
                            const token = localStorage.getItem('token');
                            
                            // Verifica se l'utente è loggato
                            if (!token) {
                                alert('Devi effettuare il login per aggiungere fumetti');
                                return;
                            }

                            // Verifica se il fumetto è già nella raccolta dell'utente
                            try {
                                const checkResponse = await fetch(`/aggiungi_fumetto_letto/${comicId}`, {
                                    headers: {
                                        'Authorization': `Bearer ${token}`
                                    }
                                });
                                
                                if (checkResponse.status === 409) {
                                    alert('Hai già aggiunto questo fumetto alla tua raccolta');
                                    return;
                                }

                                // Estrae informazioni dalla card del fumetto
                                const card = img.closest('.raccolta__card');
                                const comicTitle = img.alt;
                                const editore = card.querySelector('p:nth-child(4)').textContent.replace('Editore: ', '').trim();
                                
                                // Crea e mostra il popup per la valutazione
                                const popup = document.createElement('div');
                                popup.className = 'rating-popup';
                                popup.innerHTML = `
                                    <div class="rating-content">
                                        <h3>Valuta "${comicTitle}"</h3>
                                        <div class="stars">
                                            ${[1,2,3,4,5].map(num => `
                                                <span class="star" data-value="${num}">★</span>
                                            `).join('')}
                                        </div>
                                        <div class="rating-buttons">
                                            <button class="cancel-btn">Annulla</button>
                                            <button class="submit-btn" disabled>Conferma</button>
                                        </div>
                                    </div>
                                `;
                                document.body.appendChild(popup);

                                // Gestisce la selezione delle stelle per la valutazione
                                let selectedRating = 0;
                                const stars = popup.querySelectorAll('.star');
                                const submitBtn = popup.querySelector('.submit-btn');

                                stars.forEach(star => {
                                    star.addEventListener('click', () => {
                                        selectedRating = parseInt(star.dataset.value);
                                        // Aggiorna visualmente le stelle selezionate
                                        stars.forEach(s => {
                                            if (parseInt(s.dataset.value) <= selectedRating) {
                                                s.classList.add('active');
                                            } else {
                                                s.classList.remove('active');
                                            }
                                        });
                                        submitBtn.disabled = false;
                                    });
                                });

                                // Gestisce l'invio della valutazione
                                submitBtn.addEventListener('click', () => {
                                    // Trova i dati completi del fumetto selezionato
                                    const comicData = data.find(comic => comic.id === comicId || 
                                        comic["Nome del volume"] === comicTitle);
                                    
                                    // Estrae i dati aggiuntivi con fallback per valori mancanti
                                    const autore = comicData?.autore || 'Non specificato';
                                    const genere = comicData?.genere || 'Non specificato';
                                    const anno = comicData?.["Anno di pubblicazione"] || 'N/D';
                                    
                                    // Invia i dati al backend per salvare il fumetto e la valutazione
                                    fetch('/aggiungi_fumetto_letto', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                            'Authorization': `Bearer ${token}`
                                        },
                                        body: JSON.stringify({
                                            comic_id: comicId,
                                            titolo: comicTitle,
                                            url_copertina: img.src,
                                            autore: autore,
                                            genere: genere,
                                            editore: editore,
                                            rating: selectedRating,
                                            anno: anno
                                        })
                                    })
                                    .then(response => {
                                        if (!response.ok) {
                                            return response.json().then(errorData => {
                                                throw new Error(errorData.error || `Errore ${response.status}`);
                                            });
                                        }
                                        return response.json();
                                    })
                                    .then(data => {
                                        alert('Fumetto aggiunto alla lista dei letti!');
                                        popup.remove();
                                    })
                                    .catch(error => {
                                        console.error('Errore:', error);
                                        alert(error.message || 'Impossibile aggiungere il fumetto');
                                        popup.remove();
                                    });
                                });

                                // Gestisce la chiusura del popup
                                popup.querySelector('.cancel-btn').addEventListener('click', () => {
                                    popup.remove();
                                });

                            } catch (error) {
                                console.error('Errore:', error);
                                alert('Errore durante la verifica del fumetto');
                            }
                        });
                    });
                    
                } else {
                    // Mostra un messaggio se non ci sono risultati
                    risultatiContainer.innerHTML = '<p>Nessun risultato trovato.</p>';
                }
            })
            .catch(error => {
                // Gestisce gli errori della ricerca
                console.error('Errore:', error);
                risultatiContainer.innerHTML = '<p>Errore durante la ricerca. Riprova più tardi.</p>';
            });
    }
});