"""Mock database."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class AccountInfo:
    """Account information."""

    account_id: str
    balance: float
    account_type: str


@dataclass
class User:
    """User information."""

    username: str
    first_name: str
    last_name: str
    date_of_birth: str
    accounts: list[AccountInfo]


class MockDatabase:
    """Mock database for user authentication and account information."""

    def __init__(self):
        """Initialize the mock database with sample users."""
        self._users: Dict[str, User] = {
            "alice_smith": User(
                username="alice_smith",
                first_name="Alice",
                last_name="Smith",
                date_of_birth="1985-03-15",
                accounts=[
                    AccountInfo(
                        account_id="ACC-001", balance=3500.75, account_type="checking"
                    ),
                    AccountInfo(
                        account_id="ACC-002", balance=12000.50, account_type="savings"
                    ),
                ],
            ),
            "bob_johnson": User(
                username="bob_johnson",
                first_name="Bob",
                last_name="Johnson",
                date_of_birth="1990-07-22",
                accounts=[
                    AccountInfo(
                        account_id="ACC-003", balance=1850.25, account_type="checking"
                    ),
                    AccountInfo(
                        account_id="ACC-004",
                        balance=-450.00,
                        account_type="credit_card",
                    ),
                ],
            ),
            "carol_williams": User(
                username="carol_williams",
                first_name="Carol",
                last_name="Williams",
                date_of_birth="1978-11-08",
                accounts=[
                    AccountInfo(
                        account_id="ACC-005", balance=25000.00, account_type="savings"
                    ),
                    AccountInfo(
                        account_id="ACC-006",
                        balance=-1200.75,
                        account_type="credit_card",
                    ),
                ],
            ),
            "david_brown": User(
                username="david_brown",
                first_name="David",
                last_name="Brown",
                date_of_birth="1992-12-03",
                accounts=[
                    AccountInfo(
                        account_id="ACC-007", balance=750.00, account_type="checking"
                    ),
                    AccountInfo(
                        account_id="ACC-008", balance=5500.25, account_type="savings"
                    ),
                    AccountInfo(
                        account_id="ACC-009",
                        balance=-850.50,
                        account_type="credit_card",
                    ),
                ],
            ),
            "emma_davis": User(
                username="emma_davis",
                first_name="Emma",
                last_name="Davis",
                date_of_birth="1988-05-17",
                accounts=[
                    AccountInfo(
                        account_id="ACC-010", balance=4200.80, account_type="checking"
                    ),
                    AccountInfo(
                        account_id="ACC-011",
                        balance=-300.00,
                        account_type="credit_card",
                    ),
                ],
            ),
        }

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self._users.get(username)

    def authenticate_user(
        self, first_name: str, last_name: str, date_of_birth: str
    ) -> Optional[User]:
        """Authenticate user by personal information."""
        for user in self._users.values():
            if (
                user.first_name == first_name
                and user.last_name == last_name
                and user.date_of_birth == date_of_birth
            ):
                return user
        return None

    def get_account_info(
        self, username: str, account_type: str = "checking"
    ) -> Optional[AccountInfo]:
        """Get account information for a user by account type."""
        user = self.get_user(username)
        if not user:
            return None

        # Find the first account of the specified type
        for account in user.accounts:
            if account.account_type == account_type:
                return account

        # If no account of specified type found, return the first account
        return user.accounts[0] if user.accounts else None

    def get_all_accounts(self, username: str) -> list[AccountInfo]:
        """Get all account information for a user."""
        user = self.get_user(username)
        return user.accounts if user else []

    def get_balance(
        self, username: str, account_type: str = "checking"
    ) -> Optional[float]:
        """Get account balance for a user by account type."""
        account_info = self.get_account_info(username, account_type)
        return account_info.balance if account_info else None


# Global database instance
db = MockDatabase()


def get_database() -> MockDatabase:
    """Get the global database instance."""
    return db
