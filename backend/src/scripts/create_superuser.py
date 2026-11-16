#!/usr/bin/env python3
"""
Script to create superuser accounts.

Can be used both interactively and programmatically:
- Interactive: python src/scripts/create_superuser.py
- Programmatic: python src/scripts/create_superuser.py --username admin --email admin@example.com --password admin

Usage:
    # Interactive mode (prompts for input)
    python src/scripts/create_superuser.py

    # Non-interactive mode (with arguments)
    python src/scripts/create_superuser.py --username admin --email admin@example.com --password admin

    # Skip if exists (for initialization scripts)
    python src/scripts/create_superuser.py --username admin --email admin@example.com --password admin --skip-if-exists
"""

import argparse
import sys
from getpass import getpass

from sqlalchemy.orm import Session

from src.app.accounts.entities import User as UserEntity
from src.app.infrastructure.database_config import SessionLocal
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.use_cases.user_use_cases import pwd_context


def create_superuser_user(
    username: str,
    email: str,
    password: str,
    is_active: bool = True,
    is_staff: bool = True,
    is_superuser: bool = True,
    skip_if_exists: bool = False,
    quiet: bool = False,
) -> UserEntity | None:
    """
    Create a superuser account.

    Args:
        username: Username for the superuser
        email: Email address
        password: Plain text password (will be hashed)
        is_active: Whether user is active (default: True)
        is_staff: Whether user has staff privileges (default: True)
        is_superuser: Whether user has superuser privileges (default: True)
        skip_if_exists: If True, return None if user exists instead of raising error
        quiet: If True, suppress output messages

    Returns:
        Created UserEntity or None if user exists and skip_if_exists=True

    Raises:
        ValueError: If user already exists and skip_if_exists=False
    """
    db: Session = SessionLocal()
    user_repo = UserRepository(db)

    try:
        # Check if username already exists
        existing_user = user_repo.get_by_username(username)
        if existing_user:
            if skip_if_exists:
                if not quiet:
                    print(
                        f"✓ Superuser '{username}' already exists. Skipping creation."
                    )
                return None
            else:
                raise ValueError(f"Username '{username}' already exists!")

        # Check if email already exists
        existing_email = user_repo.get_by_email(email)
        if existing_email:
            if skip_if_exists:
                if not quiet:
                    print(f"✓ Email '{email}' already exists. Skipping creation.")
                return None
            else:
                raise ValueError(f"Email '{email}' already exists!")

        # Hash password
        hashed_password = pwd_context.hash(password)

        # Create superuser entity
        superuser = UserEntity(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )

        # Save to database
        created_user = user_repo.create(superuser)

        if not quiet:
            print(
                f"✓ Superuser created: {created_user.username} (ID: {created_user.id})"
            )
            print(f"  Username: {created_user.username}")
            print(f"  Email: {created_user.email}")

        return created_user

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def create_superuser_interactive():
    """Create superuser with interactive prompts."""
    print("=" * 60)
    print("CREATE SUPERUSER")
    print("=" * 60)

    # Get user input
    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        sys.exit(1)

    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty!")
        sys.exit(1)

    password = getpass("Password: ")
    if not password:
        print("❌ Password cannot be empty!")
        sys.exit(1)

    password_confirm = getpass("Password (again): ")
    if password != password_confirm:
        print("❌ Passwords don't match!")
        sys.exit(1)

    try:
        created_user = create_superuser_user(
            username=username,
            email=email,
            password=password,
            skip_if_exists=False,
            quiet=False,
        )

        print("\n" + "=" * 60)
        print("✅ Superuser created successfully!")
        print("=" * 60)
        print(f"Username: {created_user.username}")
        print(f"Email: {created_user.email}")
        print(f"Is Active: {created_user.is_active}")
        print(f"Is Staff: {created_user.is_staff}")
        print(f"Is Superuser: {created_user.is_superuser}")
        print("=" * 60)
        print("\n🎉 You can now login with these credentials!")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error creating superuser: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Create a superuser account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python src/scripts/create_superuser.py

  # Non-interactive mode
  python src/scripts/create_superuser.py --username admin --email admin@example.com --password admin

  # Skip if exists (for init scripts)
  python src/scripts/create_superuser.py --username admin --email admin@example.com --password admin --skip-if-exists
        """,
    )

    parser.add_argument("--username", help="Username for the superuser")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--password", help="Password (plain text, will be hashed)")
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Skip creation if user already exists (no error)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output messages")

    args = parser.parse_args()

    # If any argument is provided, use non-interactive mode
    if args.username or args.email or args.password:
        # Validate all required arguments are provided
        if not all([args.username, args.email, args.password]):
            parser.error(
                "--username, --email, and --password are all required for non-interactive mode"
            )

        try:
            created_user = create_superuser_user(
                username=args.username,
                email=args.email,
                password=args.password,
                skip_if_exists=args.skip_if_exists,
                quiet=args.quiet,
            )

            if created_user is None and args.skip_if_exists:
                sys.exit(0)  # User exists, but we skipped - success

            sys.exit(0)

        except ValueError as e:
            if not args.quiet:
                print(f"❌ Error: {e}")
            sys.exit(1)
        except Exception as e:
            if not args.quiet:
                print(f"❌ Error creating superuser: {e}")
                import traceback

                traceback.print_exc()
            sys.exit(1)
    else:
        # No arguments provided, use interactive mode
        create_superuser_interactive()


if __name__ == "__main__":
    main()
