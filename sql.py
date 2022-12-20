import pathlib
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine
from contextlib import contextmanager


def create_database():
    """
    Creates databases for each class as a SQLite database using SQL Alchemy's ORM module.
    :return: None
    """
    BASE_DIR = pathlib.Path().absolute()

    # Create a connection string to the database
    connection_string = "sqlite:///" + pathlib.Path.joinpath(BASE_DIR, "routing.db").as_posix()

    # Create engine that will be used to file to the SQLite database. Echo allows us to bypass comments produced by SQL
    engine = create_engine(connection_string, echo=True)

    # Create and configure a sessionmaker class which we use to populate each individual table.
    Session = sessionmaker(bind=engine)

    # Create mapper registry
    mapper_registry = registry()

    return Session, mapper_registry


def create_tables(engine, base):
    """
    Creates tables based on metadata provided. This will convert the __table__ attribute
    :param engine: Database engine for filing changes to DB
    :param base: Base to collect table metadata from
    :return: None
    """
    base.metadata.create_all(engine)


def create_row(obj, engine, session):
    """
    Creates a new row in a table. Corresponding table is specified in the class of the object passed to this function.
    :param obj: Object to write to table. The class of the object specifies the parameters of the table.
    :param engine: Database engine for filing changes to DB
    :param session: The session used to read and write to the table.
    :return: None
    """
    # Initialize the session. We will bind it to our engine so it knows where to write to
    local_session = session(bind=engine)

    # Add the row to the table
    local_session.add(obj)

    # Commit the row to the table
    local_session.commit()


@contextmanager
def session_scope():
    """
    Provides a transactional scope around a series of operations.
    :return: None
    """
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


# initialize SQLAlchemy objects
Session, mapper_registry = create_database()