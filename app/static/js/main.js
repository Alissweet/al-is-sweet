/**
 * AL' IS SWEET - Main JavaScript
 * Application de gestion de recettes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation
    initAnimations();
    initTooltips();
    // initCategoryManagement(); // <-- ON SUPPRIME CETTE LIGNE
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
 * Supprimer une catégorie
 */
function handleDeleteCategory(button) {
    const categoryId = button.dataset.categoryId;
    const categoryName = button.dataset.categoryName;
    
    console.log('🗑️ Tentative de suppression:', categoryId, categoryName);
    
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la famille "${categoryName}" ?`)) {
        console.log('❌ Suppression annulée par l\'utilisateur');
        return;
    }
    
    fetch(`/settings/category/delete/${categoryId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        console.log('✅ Réponse serveur:', data);
        if (data.success) {
            showMessage(data.message, 'success');
            // Recharger la page pour afficher les modifications
            setTimeout(() => {
                window.location.href = window.location.href.split('#')[0] + '#modalCategories';
                window.location.reload();
            }, 800);
        } else {
            showMessage(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Erreur:', error);
        showMessage('Erreur lors de la suppression de la catégorie', 'danger');
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