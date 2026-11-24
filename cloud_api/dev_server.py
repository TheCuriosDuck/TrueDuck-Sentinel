"""Start the local community API; administrator authentication lives in the database."""

import os  # Disable public registration.
import uvicorn  # Serve the API on loopback only.


def start():
    # No legacy publisher token is required or created.
    os.environ['SCAMLENS_ALLOW_SIGNUP'] = '0'
    print('TrueDuck Sentinel local API: http://127.0.0.1:8877/health')
    print('Public feed: http://127.0.0.1:8877/v1/feed')
    print('Anonymous reporting: http://127.0.0.1:8877/report')
    print('Administrator console: http://127.0.0.1:8877/dashboard')
    uvicorn.run('cloud_api.app:app', host='127.0.0.1', port=8877, log_level='info')


if __name__ == '__main__':
    start()
