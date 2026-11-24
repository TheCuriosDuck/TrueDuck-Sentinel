"""Create the first TrueDuck Sentinel owner account without using a public HTTP route.

From the project root on Windows, run py -3.12 -m cloud_api.manage_owner. The program uses
getpass so the password does not appear on the command line or screen.
"""

import getpass                         # Hide passwords as they are typed.
from sqlalchemy import select          # Use a parameterized account query.
from sqlalchemy.exc import IntegrityError

# Load the main API first so its community router finishes initializing.
# Importing community.py first would cause a circular-import error.
from .app import engine

# Account helpers are available after the API has completed its setup.
from .community import accounts, create_account, normalize_username


def main():
    """Ask for a username and strong password, then create one owner."""
    print('TrueDuck Sentinel — create an owner account')
    print('This is separate from the private database token and publisher token.')
    username = input('Owner username: ').strip()
    normalize_username(username)
    with engine.connect() as connection:
        # Prevent creating additional privileged users without deliberate setup.
        owner = connection.execute(select(accounts.c.id).where(accounts.c.role == 'owner')).first()
    if owner:
        print('An owner already exists. No account was changed.')
        return
    password = getpass.getpass('Choose a unique password (12+ characters): ')
    confirm = getpass.getpass('Repeat password: ')
    if password != confirm:
        print('Passwords do not match. No account was created.')
        return
    try:
        create_account(username, password, role='owner')
    except Exception as exc:
        # Avoid printing the password even if an error occurs.
        print(f'Could not create owner: {exc}')
        return
    print(f'Owner account "{username.strip().lower()}" created. Open /dashboard to sign in.')


if __name__ == '__main__':
    main()
