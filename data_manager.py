import pathlib
import validate
from sqlalchemy.orm import sessionmaker, registry
from sqlalchemy import create_engine
from contextlib import contextmanager
import pandas as pd
import time


class DataManagerMixin:
    """
    Manages data for each class as a SQLite database using SQL Alchemy's ORM module.
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

    @contextmanager
    def session_scope(self):
        """
        Provides a transactional scope around a series of operations.
        :return: None
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self):
        """
        Creates tables based on metadata provided. This will convert the __table__ attribute
        :return: None
        """
        self.mapper_registry.metadata.create_all(self.engine)

    def write_obj(self, override=1):
        """
        Creates a new row in a table. Corresponding table is specified in the class of the object passed to this function.
        :param obj: Object to write to table. The class of the object specifies the parameters of the table.
        :param override: A flag to indicate whether an object can be overridden.
        :return: None
        """
        # Add the row to the table
        with self.session_scope() as session:
            if override:
                session.merge(self)
            else:
                session.add(self)

    @classmethod
    def get_obj(cls, inc_inac=0):
        """
        Class method to initialise a class instance from file. Returns the file as an object
        :param session: Session for querying database
        :param cls: Class of object to load (directs to the relevant table)
        :param inc_inac: Flags whether inactive records should be included
        """
        while True:
            search_obj = validate.qu_input("Name or ID: ")

            # Quit if q or blank is entered
            if not search_obj:
                return 0

            # If not an id, search for instance in self.tracked_instances
            if search_obj.isnumeric():
                obj_id = search_obj
                break

            obj_id = validate.validate_obj_by_name(cls, search_obj, inc_inac=inc_inac)

            if obj_id:
                break

        # Generate and return object of class that is passed as argument
        if obj_id:
            return cls.load_obj(obj_id, inc_inac=inc_inac)

        else:
            print("Record not found.")
            return 0

    @classmethod
    def load_obj(cls, obj_id, inc_inac=0):
        """
        loads a row in a table as an object of corresponding class. Attributes for object based on table columns.
        :param cls: Class of object to load (directs to the relevant table)
        :param obj_id: Object ID to write to table. The class of the object specifies the parameters of the table.
        :param inc_inac: Flags whether inactive records should be included
        :return: None
        """
        session = cls.Session()

        # Load object from table
        obj = session.query(cls).filter(cls._id == obj_id).first()

        if inc_inac and not obj.status:
            # If set to only show active and record is inactive, return that this record is inactive.
            print("Record has been deactivated.")
            return 0

        return obj

    @classmethod
    def generate_flat_file(cls):
        """
        Generates a flat file for import. User can populate and import using read_csv()
        :param cls: Class to generate flat file
        :return: 1 if successful
        """
        # Get a list of params in the __init__ definition
        params = cls.__init__.__code__.co_varnames

        # Create a pandas dataframe with just column headings (remove init_dict) and save to csv
        flat_file = pd.DataFrame(columns=params)
        flat_file = flat_file.drop(["self", "kwargs"], axis=1)

        while True:
            try:
                filepath = validate.qu_input("Enter a file location to export the .csv to: ")

                if not filepath:
                    return 0

                flat_file.to_csv(filepath)
                print("Export successful.")
                time.sleep(1)

                return 1

            except (FileNotFoundError, OSError):
                print("File not found. Ensure the input file contains '.csv' at the end.")

    @classmethod
    def export_csv(cls, session):
        """
        Generates a flat file for import. User can populate and import using read_csv()
        :param session:
        :param cls: Class to generate flat file
        :return: 1 if successful
        """
        # Get a list of params in the __init__ definition, and remove self and kwargs
        params = cls.__init__.__code__.co_varnames[1:-1]

        # Initialize a blank list of objects to write, then populate with user's requested objects
        obj_data = []
        while True:
            obj = cls.get_obj()

            if not obj:
                break

            # Create a dict for each object, then append to list
            val_obj_dict = {param: obj.__getattribute__(param) for param in params}
            obj_data.append(val_obj_dict)

        if not obj_data:
            return 0

        # Create a pandas dataframe with column headings, then populate with data from list above
        data_export = pd.DataFrame(data=obj_data, columns=params)

        # Write to file
        while True:
            try:
                filepath = validate.qu_input("Enter a file location to export the .csv to: ")

                if not filepath:
                    return 0

                data_export.to_csv(filepath)
                print("Export successful.")
                time.sleep(1)

                return 1

            except (FileNotFoundError, OSError):
                print("File not found. Ensure the input file contains '.csv' at the end.")

    @classmethod
    def import_csv(cls, filepath=None):
        """
        Reads a file from csv and saves them as objects.
        :param cls: Class of object(s) to be created.
        :param filepath: Filepath of CSV file
        :return: 1 if successful
        """
        # TODO: Make sure this matches on ID before it imports
        while True:
            try:
                # If filepath not passed through, prompt user input
                if not filepath:
                    filepath = validate.qu_input("Enter a csv file location to load the file: ")

                # If still blank, exit
                if not filepath:
                    return 0

                import_data = pd.read_csv(filepath)
                import_data = import_data.fillna(0)
                data_dict_list = import_data.to_dict("records")

                # Loop through each dict from the import and initialize + save a new object
                for data in data_dict_list:
                    obj = cls(**data)
                    obj.write_obj()

                print("Import successful.")
                time.sleep(1)

                return 1

            except (FileNotFoundError, OSError):
                print("File not found. Ensure the input file contains '.csv' at the end.")
