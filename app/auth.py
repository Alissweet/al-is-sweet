from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from flask_mail import Message
from app import db, mail
from app.models import User
from urllib.parse import urlparse
import re
import logging

auth = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# Regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_password(password):
    if len(password) < 8: return False, "Min. 8 caractères"
    if not re.search(r'[A-Z]', password): return False, "Manque une majuscule"
    if not re.search(r'[a-z]', password): return False, "Manque une minuscule"
    if not re.search(r'[0-9]', password): return False, "Manque un chiffre"
    return True, ""

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Ravi de vous revoir, {user.username} !', 'success')
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc == '':
                return redirect(next_page)
            return redirect(url_for('main.index'))
        
        flash('Email ou mot de passe incorrect.', 'danger')
        
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('password_confirm', '')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'warning')
        elif User.query.filter_by(username=username).first():
            flash('Ce pseudo est déjà pris.', 'warning')
        elif password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
        else:
            is_valid, msg = validate_password(password)
            if not is_valid:
                flash(msg, 'danger')
            else:
                user = User(username=username, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Compte créé ! Connectez-vous.', 'success')
                return redirect(url_for('auth.login'))
                
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))

# --- RÉCUPÉRATION MOT DE PASSE ---

@auth.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            
            # Création du message
            msg = Message('Réinitialisation de votre mot de passe - Al\' is Sweet',
                          recipients=[user.email])
            
            # Lien absolu (http://...)
            link = url_for('auth.reset_token', token=token, _external=True)
            
            # Corps du mail
            msg.body = f'''Bonjour {user.username},

Pour réinitialiser votre mot de passe, cliquez sur le lien suivant :
{link}

Si vous n'avez pas fait cette demande, ignorez simplement cet email.

Gourmandisement,
L'équipe Al' is Sweet
'''
            try:
                mail.send(msg) # 🚀 ENVOI
                flash('Un email a été envoyé avec les instructions.', 'info')
                return redirect(url_for('auth.login'))
            except Exception as e:
                logger.error(f"Erreur envoi mail: {e}")
                flash("Erreur lors de l'envoi de l'email. Vérifiez votre configuration.", "danger")
        else:
            flash('Aucun compte associé à cet email.', 'warning')
            
    return render_template('reset_request.html')

@auth.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('Le lien est invalide ou a expiré.', 'warning')
        return redirect(url_for('auth.reset_request'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
        else:
            is_valid, msg = validate_password(password)
            if not is_valid:
                flash(msg, 'danger')
            else:
                user.set_password(password)
                db.session.commit()
                flash('Votre mot de passe a été mis à jour !', 'success')
                return redirect(url_for('auth.login'))
                
    return render_template('reset_token.html')