/**
 * AL' IS SWEET - Main JavaScript
 * Application de gestion de recettes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation
    initAnimations();
    initTooltips();
    initCategoryManagement();
	autoCloseAlerts();
});

/**
 * Animations d'entrée pour les cartes de recettes
 */
function initAnimations() {
    const cards = document.querySelectorAll('.recipe-card');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(card);
    });
}

/**
 * Initialise les tooltips Bootstrap
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
}

/**
 * Fermeture automatique des alertes flash après 3 secondes
 */
function autoCloseAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            // Fade out élégant
            alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 500);
        }, 2000); // 3 secondes
    });
}

/**
 * Fonction utilitaire pour formater les nombres
 */
function formatNumber(num, decimals = 1) {
    return parseFloat(num).toFixed(decimals).replace(/\.0+$/, '');
}

/**
 * ========================================
 * GESTION DES CATÉGORIES (AJAX)
 * ========================================
 */
function initCategoryManagement() {
    console.log('🔧 Initialisation de la gestion des catégories');
    
    // Utiliser la délégation d'événements sur le document pour capturer tous les événements
    // même si les éléments sont ajoutés dynamiquement
    
    // Gestion de l'ajout de catégorie
    document.addEventListener('submit', function(e) {
        if (e.target && e.target.id === 'formAjoutCategorie') {
            console.log('📝 Formulaire d\'ajout détecté');
            e.preventDefault();
            e.stopPropagation();
            handleAddCategory(e);
        }
    });

    // Gestion de la modification de catégorie
    document.addEventListener('submit', function(e) {
        if (e.target && e.target.classList.contains('formEditCategorie')) {
            console.log('✏️ Formulaire d\'édition détecté');
            e.preventDefault();
            e.stopPropagation();
            handleEditCategory(e);
        }
    });

    // Gestion de la suppression de catégorie
    document.addEventListener('click', function(e) {
        if (e.target.closest('.btnDeleteCategory')) {
            console.log('🗑️ Bouton de suppression détecté');
            e.preventDefault();
            e.stopPropagation();
            const btn = e.target.closest('.btnDeleteCategory');
            handleDeleteCategory(btn);
        }
    });
}

/**
 * Ajouter une catégorie
 */
function handleAddCategory(e) {
    console.log('📝 handleAddCategory appelé');
    
    const form = e.target;
    const formData = new FormData(form);
    
    console.log('📤 Envoi des données:', formData.get('category_name'));
    
    fetch('/settings/category/add', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('📥 Réponse reçue:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('✅ Données JSON:', data);
        if (data.success) {
            showMessage(data.message, 'success');
            // Vider le champ input
            form.reset();
            // Recharger la page pour afficher la nouvelle catégorie
            setTimeout(() => {
                window.location.href = window.location.href.split('#')[0] + '#modalCategories';
                window.location.reload();
            }, 800);
        } else {
            showMessage(data.message, 'warning');
        }
    })
    .catch(error => {
        console.error('❌ Erreur:', error);
        showMessage('Erreur lors de l\'ajout de la catégorie', 'danger');
    });
}

/**
 * Modifier une catégorie
 */
function handleEditCategory(e) {
    console.log('✏️ handleEditCategory appelé');
    
    const form = e.target;
    const formData = new FormData(form);
    const categoryId = form.dataset.categoryId;
    
    console.log('📤 Modification catégorie ID:', categoryId, 'Nouveau nom:', formData.get('new_name'));
    
    fetch(`/settings/category/edit/${categoryId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('📥 Réponse reçue:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('✅ Données JSON:', data);
        if (data.success) {
            showMessage(data.message, 'success');
            // Recharger la page pour afficher les modifications
            setTimeout(() => {
                window.location.href = window.location.href.split('#')[0] + '#modalCategories';
                window.location.reload();
            }, 800);
        } else {
            showMessage(data.message, 'warning');
        }
    })
    .catch(error => {
        console.error('❌ Erreur:', error);
        showMessage('Erreur lors de la modification de la catégorie', 'danger');
    });
}

/**
 * Supprimer une catégorie — avec modale Bootstrap
 */
function handleDeleteCategory(button) {
    const categoryId = button.dataset.categoryId;
    const categoryName = button.dataset.categoryName;

    // Remplir la modale avec le nom de la catégorie
    document.getElementById('deleteCategoryName').textContent = `"${categoryName}"`;

    // Afficher la modale Bootstrap
    const modalEl = document.getElementById('deleteCategoryModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    // Quand on clique sur "Oui, supprimer"
    const confirmBtn = document.getElementById('confirmDeleteCategory');

    // Nettoyer l'ancien listener pour éviter les doublons
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', function() {
        // Feedback visuel sur le bouton
        newConfirmBtn.disabled = true;
        newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Suppression...';

        const formData = new FormData();
        formData.append('csrf_token', document.querySelector('meta[name="csrf-token"]')?.content 
            || document.querySelector('input[name="csrf_token"]')?.value || '');

        fetch(`/settings/category/delete/${categoryId}`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            modal.hide();
            if (data.success) {
                // Supprimer la ligne visuellement
                const row = document.getElementById(`cat-row-${categoryId}`);
                if (row) {
                    row.style.transition = 'opacity 0.3s ease';
                    row.style.opacity = '0';
                    setTimeout(() => row.remove(), 300);
                }
                showMessage(data.message, 'success');
            } else {
                showMessage(data.message, 'danger');
            }
        })
        .catch(error => {
            modal.hide();
            console.error('Erreur:', error);
            showMessage('Erreur lors de la suppression.', 'danger');
        });
    });
}

/**
 * Afficher un message de notification
 */
function showMessage(message, type = 'info') {
    // Créer l'élément d'alerte Bootstrap
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Supprimer automatiquement après 3 secondes
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

/**
 * ═══════════════════════════════════════════════
 * LISTE DE COURSES MULTI-RECETTES
 * ═══════════════════════════════════════════════
 */

let selectedRecipeIds = new Set(
    JSON.parse(sessionStorage.getItem('selectedRecipes') || '[]')
);

document.addEventListener('DOMContentLoaded', function() {
    _syncSelectionUI();
});

function handleCardClick(event, recipeId, recipeUrl) {
    if (selectedRecipeIds.size > 0) {
        const checkEl = document.getElementById('check-' + recipeId);
        toggleRecipeSelect(recipeId, checkEl);
    } else {
        window.location = recipeUrl;
    }
}

function toggleRecipeSelect(recipeId, el) {
    if (selectedRecipeIds.has(recipeId)) {
        selectedRecipeIds.delete(recipeId);
    } else {
        selectedRecipeIds.add(recipeId);
    }
    _saveSelection();
    _syncSelectionUI();
}

function toggleAllRows(masterCheckbox) {
    document.querySelectorAll('.row-check').forEach(cb => {
        const row = cb.closest('tr');
        const recipeId = parseInt(row.dataset.recipeId);
        if (masterCheckbox.checked) {
            selectedRecipeIds.add(recipeId);
            cb.checked = true;
        } else {
            selectedRecipeIds.delete(recipeId);
            cb.checked = false;
        }
    });
    _saveSelection();
    _syncSelectionUI();
}

function clearSelection() {
    selectedRecipeIds.clear();
    _saveSelection();
    _syncSelectionUI();
}

function goToShoppingList() {
    if (selectedRecipeIds.size === 0) return;
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/shopping-list';
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'recipe_ids';
    input.value = Array.from(selectedRecipeIds).join(',');
    form.appendChild(input);
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content
              || document.querySelector('input[name="csrf_token"]')?.value || '';
    if (csrf) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrf;
        form.appendChild(csrfInput);
    }
    document.body.appendChild(form);
    form.submit();
}

function _saveSelection() {
    sessionStorage.setItem('selectedRecipes', JSON.stringify(Array.from(selectedRecipeIds)));
}

function _syncSelectionUI() {
    const count = selectedRecipeIds.size;
    const bar = document.getElementById('shoppingBar');
    const countEl = document.getElementById('shoppingBarCount');
    if (bar) {
        if (count > 0) {
            bar.classList.remove('d-none');
            bar.classList.add('d-flex');
        } else {
            bar.classList.add('d-none');
            bar.classList.remove('d-flex');
        }
    }
    if (countEl) countEl.textContent = count;

    document.querySelectorAll('[id^="check-"]').forEach(circle => {
        const id = parseInt(circle.id.replace('check-', ''));
        const card = document.getElementById('card-' + id);
        if (selectedRecipeIds.has(id)) {
            circle.classList.add('active');
            card?.classList.add('card-selected');
        } else {
            circle.classList.remove('active');
            card?.classList.remove('card-selected');
        }
    });

    document.querySelectorAll('.row-check').forEach(cb => {
        const row = cb.closest('tr');
        if (!row) return;
        const recipeId = parseInt(row.dataset.recipeId);
        cb.checked = selectedRecipeIds.has(recipeId);
    });
}


/**
 * ═══════════════════════════════════════════════
 * GESTION DES FAVORIS
 * ═══════════════════════════════════════════════
 */
function toggleFavorite(recipeId, btnElement) {
    // Récupération du token CSRF (depuis une meta ou un input caché global)
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                      document.querySelector('meta[name="csrf-token"]')?.content;

    // Animation immédiate pour l'UX (Optimistic UI)
    const icon = btnElement.querySelector('i');
    const isActive = btnElement.classList.contains('active');
    
    // Toggle visuel temporaire
    btnElement.classList.toggle('active');
    icon.className = isActive ? 'bi bi-heart' : 'bi bi-heart-fill';

    fetch(`/recipe/${recipeId}/favorite`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Erreur réseau');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Confirmation visuelle finale
            if (data.is_favorite) {
                btnElement.classList.add('active');
                icon.className = 'bi bi-heart-fill';
                // Petit effet de pop
                icon.style.transform = 'scale(1.3)';
                setTimeout(() => icon.style.transform = 'scale(1)', 200);
            } else {
                btnElement.classList.remove('active');
                icon.className = 'bi bi-heart';
            }
        } else {
            // Revert en cas d'erreur logique
            console.error(data.message);
            btnElement.classList.toggle('active'); // On annule
        }
    })
    .catch(error => {
        console.error('Erreur:', error);
        // Revert en cas d'erreur technique
        btnElement.classList.toggle('active');
        icon.className = isActive ? 'bi bi-heart-fill' : 'bi bi-heart';
        alert("Impossible de modifier les favoris pour l'instant.");
    });
}

/**
 * ═══════════════════════════════════════════════
 * SYSTÈME DE NOTATION (RATING)
 * ═══════════════════════════════════════════════
 */
function rateRecipe(button) {
    const value = button.dataset.value;
    const recipeId = button.dataset.recipeId;
    
    // Récupération du token CSRF
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                      document.querySelector('meta[name="csrf-token"]')?.content;

    if (!csrfToken) {
        console.error("Token CSRF introuvable");
        return;
    }

    // Appel AJAX
    fetch(`/recipe/${recipeId}/rate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `rating=${value}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateRatingUI(button, data.rating);
        } else {
            console.error(data.message);
        }
    })
    .catch(error => console.error('Erreur:', error));
}

function updateRatingUI(clickedBtn, activeValue) {
    const container = clickedBtn.closest('.rating-pills');
    const feedback = document.getElementById('ratingFeedback');
    
    // Textes de feedback (doivent correspondre à ceux du template)
    const labels = [
        '', 
        'Recette à améliorer', 
        'Recette correcte', 
        'Bonne recette !', 
        'Très bonne recette !', 
        '✨ Recette incontournable !'
    ];

    // 1. Reset visuel de tous les boutons
    container.querySelectorAll('.rating-pill').forEach(btn => {
        btn.classList.remove('active', 'just-rated');
    });

    // 2. Activation du bouton sélectionné (si une note existe)
    if (activeValue) {
        // On retrouve le bouton qui correspond à la valeur retournée par le serveur
        const targetBtn = container.querySelector(`.rating-pill[data-value="${activeValue}"]`);
        if (targetBtn) {
            targetBtn.classList.add('active', 'just-rated');
        }
        
        // Mise à jour du texte
        if (feedback) {
            feedback.textContent = labels[activeValue];
            feedback.style.opacity = '1';
        }
    } else {
        // Si la note a été retirée (toggle off)
        if (feedback) {
            feedback.style.opacity = '0';
            setTimeout(() => { feedback.textContent = ''; }, 300);
        }
    }
}


/**
 * ═══════════════════════════════════════════════
 * GESTION DES FILTRES COMBINÉS
 * ═══════════════════════════════════════════════
 */
function selectCategory(categoryName) {
    // 1. Mettre à jour le champ caché
    const input = document.getElementById('categoryInput');
    if (input) {
        input.value = categoryName;
        
        // 2. Soumettre le formulaire global
        const form = document.getElementById('filterForm');
        if (form) {
            form.submit();
        }
    }
}

function markAsCooked(recipeId) {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                      document.querySelector('meta[name="csrf-token"]')?.content;

    fetch(`/recipe/${recipeId}/cooked`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, 'success');
        } else {
            showMessage(data.message, 'danger');
        }
    });
}

/**
 * Réouvrir la modale après rechargement
 */
window.addEventListener('load', function() {
    console.log('🔄 Page chargée, hash actuel:', window.location.hash);
    // Vérifier les deux possibilités d'ancre
    if (window.location.hash === '#settingsModal' || window.location.hash === '#modalCategories') {
        console.log('🔓 Réouverture de la modale...');
        const modalElement = document.getElementById('settingsModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            // Mettre à jour l'onglet Familles
            const tabButton = document.querySelector('[data-bs-target="#tab-categories"]');
            if (tabButton) {
                tabButton.click();
            }
        } else {
            console.error('❌ Modal settingsModal introuvable');
        }
    }
});