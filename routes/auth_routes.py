from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, current_user
from flask_dance.contrib.google import google
from services.auth_service import AuthService
from urllib.parse import urlparse, urljoin
from extensions import limiter
import secrets
from datetime import datetime, timedelta, UTC
import traceback


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def is_safe_url(target):
    """
    Check if the target URL is safe for redirects (prevents open redirect vulnerability)

    Args:
        target: The URL to validate

    Returns:
        True if URL is safe (same host), False otherwise
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login')
@limiter.limit("10 per minute")
def login():
    """Login page with Google sign-in button"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@auth_bp.route('/google')
@limiter.limit("10 per minute")
def google_login():
    """Initiate Google OAuth flow with CSRF protection via state parameter"""
    # Generate secure state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session['oauth_state_expires'] = datetime.now(UTC) + timedelta(minutes=10)

    current_app.logger.info(f"Generated OAuth state token for new login attempt")

    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('auth.google_callback'))


@auth_bp.route('/google/callback')
@limiter.limit("5 per minute")
def google_callback():
    """Handle Google OAuth callback with state validation"""
    try:
        # CRITICAL: Validate OAuth state parameter to prevent CSRF attacks
        received_state = request.args.get('state')
        expected_state = session.pop('oauth_state', None)
        state_expires = session.pop('oauth_state_expires', None)

        # Check state parameter exists
        if not received_state or not expected_state:
            current_app.logger.warning("OAuth callback missing state parameter")
            flash("Invalid authentication state. Please try again.", "danger")
            return redirect(url_for('auth.login'))

        # Validate state matches
        if received_state != expected_state:
            current_app.logger.error(f"OAuth state mismatch. Expected: {expected_state[:10]}..., Got: {received_state[:10]}...")
            flash("Invalid authentication state. Possible CSRF attack detected.", "danger")
            return redirect(url_for('auth.login'))

        # Check state hasn't expired
        if state_expires:
            try:
                if datetime.now(UTC) > state_expires:
                    current_app.logger.warning("OAuth state token expired")
                    flash("Authentication session expired. Please try again.", "danger")
                    return redirect(url_for('auth.login'))
            except (TypeError, ValueError) as e:
                current_app.logger.error(f"Error checking state expiration: {e}")

        current_app.logger.info("OAuth state validation successful")

        # Check if OAuth was successful
        if not google.authorized:
            error_msg = 'Google authentication failed. Please try again.'
            current_app.logger.error(f"OAuth not authorized. Token: {google.token}")
            flash(error_msg, 'danger')
            return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Error in OAuth callback: {str(e)}", exc_info=True)
        flash(f'OAuth error: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

    # Get user info from Google
    try:
        current_app.logger.info("Fetching user info from Google...")
        resp = google.get('/oauth2/v2/userinfo')
        current_app.logger.info(f"Google API response status: {resp.status_code}")

        if not resp.ok:
            current_app.logger.error(f"Google API error: {resp.text}")
            flash('Failed to fetch user information from Google.', 'danger')
            return redirect(url_for('auth.login'))

        google_info = resp.json()
        google_id = google_info.get('id')
        email = google_info.get('email')
        name = google_info.get('name')

        current_app.logger.info(f"Got user info - ID: {google_id}, Email: {email}, Name: {name}")

        # Validate we received the required scopes (id and email)
        if not google_id or not email:
            current_app.logger.error(f"Insufficient permissions from Google. ID: {bool(google_id)}, Email: {bool(email)}")
            flash('Insufficient permissions from Google. Please grant access to your profile and email.', 'danger')
            return redirect(url_for('auth.login'))

    except Exception as e:
        current_app.logger.error(f"Exception in OAuth callback: {str(e)}", exc_info=True)
        flash(f'An error occurred during authentication: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

    # Check if user already has a linked account
    try:
        user = AuthService.get_user_from_google(google_id, email, name)

        if user:
            # User exists, log them in
            # CRITICAL: Regenerate session ID to prevent session fixation attacks
            # Preserve necessary session data before regeneration
            old_session_data = {k: session[k] for k in list(session.keys())}
            session.clear()
            # Restore preserved data (but not oauth_state which was already consumed)
            for key, value in old_session_data.items():
                if key not in ('oauth_state', 'oauth_state_expires'):
                    session[key] = value
            session.modified = True
            session.permanent = True

            login_user(user, remember=True)
            current_app.logger.info(f"User {user.id} logged in successfully, session regenerated")
            flash(f'Welcome back, {user.name}!', 'success')

            # Redirect to next page or dashboard (validate URL to prevent open redirect)
            next_page = request.args.get('next')
            if next_page and not is_safe_url(next_page):
                next_page = None
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            # No linked account, redirect to registration
            session['google_id'] = google_id
            session['google_email'] = email
            session['google_name'] = name
            flash('Please link your Google account to an existing player profile.', 'info')
            return redirect(url_for('auth.register'))
    except Exception as e:
        current_app.logger.error(f"Error processing user login: {str(e)}", exc_info=True)
        flash(f'Login error: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    """Registration page to link Google account to player"""
    # Check if we have Google info in session
    google_id = session.get('google_id')
    google_email = session.get('google_email')
    google_name = session.get('google_name')

    if not google_id:
        flash('No Google account information found. Please sign in with Google first.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        action = request.form.get('action', 'link')  # 'link' or 'create'

        if action == 'create':
            # Create new player profile
            new_name = request.form.get('new_name', '').strip()
            new_email = request.form.get('new_email', '').strip()
            favorite_color = request.form.get('favorite_color', '#2e7d32').strip()

            if not new_name:
                flash('Please enter a name for your player profile.', 'warning')
                return redirect(url_for('auth.register'))

            # Create and link new player
            success, message, user = AuthService.create_and_link_player(
                google_id=google_id,
                name=new_name,
                email=new_email or google_email,
                favorite_color=favorite_color
            )

            if success:
                # CRITICAL: Regenerate session ID to prevent session fixation attacks
                old_session_data = {k: session[k] for k in list(session.keys())}
                session.clear()
                # Don't restore Google info - user is now authenticated
                session.modified = True
                session.permanent = True

                # Log user in
                login_user(user, remember=True)
                current_app.logger.info(f"New user {user.id} created and logged in, session regenerated")
                flash(f'Profile created successfully! Welcome, {user.name}!', 'success')
                return redirect(url_for('main.index'))
            else:
                flash(message, 'danger')
                return redirect(url_for('auth.register'))

        else:  # action == 'link'
            # Link to existing player
            player_id = request.form.get('player_id')

            if not player_id:
                flash('Please select a player to link your account to.', 'warning')
                return redirect(url_for('auth.register'))

            # Link Google account to player
            success, message, user = AuthService.link_google_to_player(google_id, player_id)

            if success:
                # CRITICAL: Regenerate session ID to prevent session fixation attacks
                old_session_data = {k: session[k] for k in list(session.keys())}
                session.clear()
                # Don't restore Google info - user is now authenticated
                session.modified = True
                session.permanent = True

                # Log user in
                login_user(user, remember=True)
                current_app.logger.info(f"User {user.id} linked Google account and logged in, session regenerated")
                flash(f'Account linked successfully! Welcome, {user.name}!', 'success')
                return redirect(url_for('main.index'))
            else:
                flash(message, 'danger')
                return redirect(url_for('auth.register'))

    # GET request - show registration form
    unlinked_players = AuthService.get_unlinked_players()

    return render_template('auth/register.html',
                         google_name=google_name,
                         google_email=google_email,
                         unlinked_players=unlinked_players)


@auth_bp.route('/logout')
def logout():
    """Logout route"""
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/unauthorized')
def unauthorized():
    """Unauthorized access page"""
    return render_template('auth/unauthorized.html'), 403
