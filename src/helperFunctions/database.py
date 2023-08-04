from __future__ import annotations

from contextlib import contextmanager
from typing import Generic, TypeVar, Iterator

from storage.db_interface_base import ReadOnlyDbInterface

DatabaseInterface = TypeVar('DatabaseInterface', bound=ReadOnlyDbInterface)


# FIXME this class does nothing and can be removed
class ConnectTo(Generic[DatabaseInterface]):
    """
    Open a database connection using the interface passed to the constructor. Intended to be used as a context manager.

    :param connected_interface: A database interface from the `storage` module (e.g. `FrontEndDbInterface`)

    :Example:

        .. code-block:: python

           with ConnectTo(FrontEndDbInterface) as connection:
                query = connection.firmwares.find({})
    """

    def __init__(self, connected_interface: type[DatabaseInterface]):
        self.interface = connected_interface
        self.connection: DatabaseInterface | None = None

    def __enter__(self) -> DatabaseInterface:
        self.connection = self.interface()
        return self.connection

    def __exit__(self, *args):
        pass


@contextmanager
def get_shared_session(database: DatabaseInterface) -> Iterator[DatabaseInterface]:
    with database.get_read_only_session():
        yield database
