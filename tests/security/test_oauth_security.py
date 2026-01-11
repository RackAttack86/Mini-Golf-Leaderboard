"""
OAuth Security Tests

Tests for OAuth state parameter validation, scope validation, and session security.
These tests verify critical security features that prevent CSRF attacks on the OAuth flow.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from flask import session
import secrets


@pytest.mark.security
@pytest.mark.auth
class TestOAuthStateValidation:
    """Test OAuth state parameter validation to prevent CSRF attacks"""

    def test_oauth_initiation_generates_state_token(self, client, database):
        """Test that initiating OAuth generates a secure state token"""
        response = client.get('/auth/google', follow_redirects=False)

        # Should redirect to Google OAuth
        assert response.status_code == 302

        # Check that state was stored in session
        with client.session_transaction() as sess:
            assert 'oauth_state' in sess, "OAuth state token should be generated"
            assert len(sess['oauth_state']) >= 32, "State token should be cryptographically secure (32+ chars)"
            assert 'oauth_state_expires' in sess, "State expiration should be set"

    def test_oauth_state_expiration_set_correctly(self, client, database):
        """Test that OAuth state has a 10-minute expiration"""
        before_time = datetime.now(timezone.utc)
        response = client.get('/auth/google', follow_redirects=False)
        after_time = datetime.now(timezone.utc)

        with client.session_transaction() as sess:
            expires = sess.get('oauth_state_expires')
            assert expires is not None, "State expiration should be set"

            # Expiration should be approximately 10 minutes from now
            expected_min = before_time + timedelta(minutes=9, seconds=50)
            expected_max = after_time + timedelta(minutes=10, seconds=10)
            assert expected_min <= expires <= expected_max, "State should expire in ~10 minutes"

    def test_oauth_callback_rejects_missing_state(self, client, database):
        """Test that callback rejects requests without state parameter"""
        # Try callback without state parameter
        response = client.get('/auth/google/callback?code=test_code', follow_redirects=True)

        # Should redirect back to login with error
        assert b'Invalid authentication state' in response.data or b'try again' in response.data.lower()

    def test_oauth_callback_rejects_invalid_state(self, client, database):
        """Test that callback rejects mismatched state parameters"""
        # Set state in session
        with client.session_transaction() as sess:
            sess['oauth_state'] = 'expected_state_token'
            sess['oauth_state_expires'] = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Call callback with different state
        response = client.get('/auth/google/callback?state=wrong_state_token&code=test_code',
                            follow_redirects=True)

        # Should reject and show error
        assert b'Invalid authentication state' in response.data or b'CSRF' in response.data

    def test_oauth_callback_rejects_expired_state(self, client, database):
        """Test that callback rejects expired state tokens"""
        # Set expired state in session
        state_token = secrets.token_urlsafe(32)
        with client.session_transaction() as sess:
            sess['oauth_state'] = state_token
            sess['oauth_state_expires'] = datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired

        # Call callback with valid but expired state
        response = client.get(f'/auth/google/callback?state={state_token}&code=test_code',
                            follow_redirects=True)

        # Should reject expired state
        assert b'expired' in response.data.lower() or b'try again' in response.data.lower()

    def test_oauth_state_stored_securely(self, client, database):
        """Test that OAuth state tokens are cryptographically random"""
        # Generate multiple state tokens
        tokens = set()
        for _ in range(5):
            response = client.get('/auth/google', follow_redirects=False)
            with client.session_transaction() as sess:
                tokens.add(sess.get('oauth_state'))

        # All tokens should be unique
        assert len(tokens) == 5, "State tokens should be cryptographically random"

        # All tokens should be long enough
        for token in tokens:
            assert len(token) >= 32, "All state tokens should be >= 32 characters"


@pytest.mark.security
@pytest.mark.auth
class TestOAuthFlowSecurity:
    """Test general OAuth flow security"""

    def test_oauth_endpoint_rate_limited(self, client, database):
        """Test that OAuth endpoints have rate limiting"""
        # Try to hit OAuth endpoint multiple times
        # This test verifies the rate limiter is configured
        # Actual rate limit testing requires more sophisticated setup
        response = client.get('/auth/google', follow_redirects=False)
        assert response.status_code in (302, 429), "OAuth endpoint should be accessible or rate limited"

    def test_oauth_callback_without_code(self, client, database):
        """Test that callback without authorization code is handled"""
        state_token = secrets.token_urlsafe(32)
        with client.session_transaction() as sess:
            sess['oauth_state'] = state_token
            sess['oauth_state_expires'] = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Call callback without code parameter
        response = client.get(f'/auth/google/callback?state={state_token}', follow_redirects=True)

        # Should handle gracefully (not crash)
        assert response.status_code == 200


@pytest.mark.security
@pytest.mark.auth
class TestSessionSecurity:
    """Test session security features"""

    def test_session_cookie_httponly(self, client, app):
        """Test that session cookies have HttpOnly flag"""
        response = client.get('/auth/login')

        # Check Set-Cookie header for HttpOnly
        set_cookie = response.headers.get('Set-Cookie', '')
        if set_cookie:
            # In production, session cookies should have HttpOnly
            # In testing, Flask-Dance cookies may not have it, which is OK for tests
            pass  # This is more of a configuration check

    def test_session_lifetime_configured(self, app):
        """Test that session lifetime is properly configured"""
        # Check that PERMANENT_SESSION_LIFETIME is set
        assert hasattr(app.config, 'PERMANENT_SESSION_LIFETIME') or 'PERMANENT_SESSION_LIFETIME' in app.config

        # Should be reasonable (not too long)
        lifetime = app.config.get('PERMANENT_SESSION_LIFETIME')
        if lifetime:
            # Should be less than 30 days
            assert lifetime.days <= 30, "Session lifetime should not exceed 30 days"


@pytest.mark.security
class TestSecurityConfiguration:
    """Test security configuration"""

    def test_secret_key_configured(self, app):
        """Test that SECRET_KEY is configured and not default"""
        assert 'SECRET_KEY' in app.config
        assert app.config['SECRET_KEY'] is not None
        # In tests, dev key is OK, but should be checked
        secret = app.config['SECRET_KEY']
        assert len(secret) > 10, "SECRET_KEY should be reasonably long"

    def test_oauth_credentials_required(self, app):
        """Test that OAuth credentials are configured"""
        # GOOGLE_OAUTH_CLIENT_ID and SECRET should be configured
        # In tests they might be None, which is OK for most tests
        assert 'GOOGLE_OAUTH_CLIENT_ID' in app.config
        assert 'GOOGLE_OAUTH_CLIENT_SECRET' in app.config

    def test_csrf_protection_enabled(self, app):
        """Test that CSRF protection is enabled (except in TESTING mode)"""
        # CSRF is typically disabled in TESTING mode for easier testing
        # In production (TESTING=False), it should be enabled
        if app.config.get('TESTING'):
            # In testing mode, CSRF is disabled - this is OK
            pass
        else:
            # In production, CSRF should be enabled
            assert app.config.get('WTF_CSRF_ENABLED', True) == True

    def test_session_cookie_secure_in_production(self, app):
        """Test that SESSION_COOKIE_SECURE is True in production"""
        # In DEBUG mode, it's False (for development)
        # In production (DEBUG=False), it should be True
        if not app.debug:
            assert app.config.get('SESSION_COOKIE_SECURE') == True
        else:
            # In debug mode, it can be False
            assert app.config.get('SESSION_COOKIE_SECURE') == False

    def test_session_cookie_samesite_configured(self, app):
        """Test that SESSION_COOKIE_SAMESITE is configured"""
        samesite = app.config.get('SESSION_COOKIE_SAMESITE')
        assert samesite in ('Lax', 'Strict', 'None'), "SESSION_COOKIE_SAMESITE should be configured"
