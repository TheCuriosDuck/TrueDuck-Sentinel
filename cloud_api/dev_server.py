"""Start a local cloud API demo with a separate randomly generated publish token."""

# The demo uses loopback only: it is never exposed to the internet.
import os                              # Pass the secret to the API process.
import secrets                         # Create a cryptographically random token.
from pathlib import Path               # Write the token inside ignored data/.
import uvicorn                         # Run the FastAPI app in development mode.

DATA_DIR = Path(__file__).resolve().parent / 'data'
TOKEN_FILE = DATA_DIR / 'publisher_token.txt'


def start():
    """Reuse the local demo token so publishing works across restarts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TOKEN_FILE.exists():
        # This token is for the LOCAL cloud demo; hosted deployments use secrets.
        TOKEN_FILE.write_text(secrets.token_urlsafe(48), encoding='utf-8')
        try:
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass
    # Only the local demo enables reporter self-registration.
    # Hosted systems should leave registration disabled until abuse controls are deployed.
    os.environ.setdefault('SCAMLENS_ALLOW_SIGNUP', '1')
    os.environ['SCAMLENS_PUBLISH_TOKEN'] = TOKEN_FILE.read_text(encoding='utf-8').strip()
    print('TrueDuck Sentinel cloud demo API: http://127.0.0.1:8877/health')
    print('Public feed: http://127.0.0.1:8877/v1/feed')
    print('Community console: http://127.0.0.1:8877/dashboard')
    print('The separate publisher token is saved in cloud_api/data (do not share it).')
    uvicorn.run('cloud_api.app:app', host='127.0.0.1', port=8877, log_level='info')


if __name__ == '__main__':
    start()
