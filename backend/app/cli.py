import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trusted local account provisioning commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_user = subparsers.add_parser(
        "create-privileged-user",
        help="Create an instructor or admin account from a trusted terminal.",
    )
    create_user.add_argument("--email", required=True)
    create_user.add_argument("--full-name", required=True)
    create_user.add_argument(
        "--role",
        choices=[UserRole.INSTRUCTOR.value, UserRole.ADMIN.value],
        required=True,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    full_name = " ".join(args.full_name.split())
    if len(full_name) < 2:
        raise SystemExit("Full name must contain at least two characters.")

    password = getpass("Password (minimum 10 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters.")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")

    with SessionLocal() as db:
        existing = db.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            raise SystemExit("An account with that email already exists; no changes were made.")
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=args.role,
        )
        db.add(user)
        db.commit()
        print(f"Created {args.role} account for {email} (user id: {user.id}).")


if __name__ == "__main__":
    main()
