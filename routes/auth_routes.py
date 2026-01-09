from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, current_user
from flask_dance.contrib.google import google
from services.auth_service import AuthService
from urllib.parse import urlparse, urljoin
from extensions import limiter


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
    """Initiate Google OAuth flow"""
    # Note: Flask-Dance handles OAuth state parameter validation internally
    # We don't need to manually generate/validate state tokens
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('auth.google_callback'))


@auth_bp.route('/google/callback')
@limiter.limit("5 per minute")
def google_callback():
    """Handle Google OAuth callback"""
    # Note: Flask-Dance validates the OAuth state parameter automatically
    # If state validation fails, google.authorized will be False
    from flask import current_app
    import traceback

    try:
        # Log for debugging
        current_app.logger.info(f"Google callback invoked, authorized: {google.authorized}")

        # Check if OAuth was successful
        if not google.authorized:
            error_msg = 'Google authentication failed. Please try again.'
            current_app.logger.error(f"OAuth not authorized. Token: {google.token}")
            flash(error_msg, 'danger')
            return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Error checking OAuth authorization: {str(e)}", exc_info=True)
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

        if not google_id or not email:
            current_app.logger.error("Missing required Google info")
            flash('Failed to get required information from Google.', 'danger')
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
            # Regenerate session to prevent session fixation attacks
            session.permanent = True
            session.modified = True

            login_user(user, remember=True)
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
                # Clear session data
                session.pop('google_id', None)
                session.pop('google_email', None)
                session.pop('google_name', None)

                # Regenerate session to prevent session fixation attacks
                session.permanent = True
                session.modified = True

                # Log user in
                login_user(user, remember=True)
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
                # Clear session data
                session.pop('google_id', None)
                session.pop('google_email', None)
                session.pop('google_name', None)

                # Regenerate session to prevent session fixation attacks
                session.permanent = True
                session.modified = True

                # Log user in
                login_user(user, remember=True)
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
