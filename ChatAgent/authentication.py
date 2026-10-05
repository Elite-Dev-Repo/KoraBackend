import hashlib
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIKey

class APIKeyHeaderAuthentication(BaseAuthentication):
    """
    Custom authentication class that parses the API key from 
    either the 'X-Api-Key' header or the standard 'Authorization' header.
    """
    def authenticate(self, request):
        # 1. Look for custom header 'X-Api-Key'
        api_key = request.META.get('HTTP_X_API_KEY')

        # 2. Fallback: Look for 'Authorization: Api-Key <token>'
        if not api_key:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Api-Key '):
                api_key = auth_header.split(' ')[1]

        # If no key in header, return None to allow unauthenticated or next auth class
        if not api_key:
            return None

        # 3. Hash the incoming key to match the database stored hash
        hashed_input_key = hashlib.sha256(api_key.encode()).hexdigest()

        # 4. Query database for matching active key
        try:
            key_obj = APIKey.objects.select_related('user').get(
                key_hash=hashed_input_key, 
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive API key.')

        # 5. Return (user, auth) tuple to set request.user and request.auth
        return (key_obj.user, key_obj)

    def authenticate_header(self, request):
        """
        Returns a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthenticated response.
        """
        return 'Api-Key realm="API"'