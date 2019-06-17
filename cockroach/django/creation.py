from django.db.backends.postgresql.creation import DatabaseCreation as PostgresDatabaseCreation

class DatabaseCreation(PostgresDatabaseCreation):
    data_types = dict(PostgresDatabaseCreation.data_types,
                      AutoField='integer',
                     )

