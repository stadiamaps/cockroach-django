from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PostgresDatabaseWrapper
from django.db.backends.postgresql_psycopg2.base import CursorWrapper
#from django.db.backends import * 
from django.db.backends.signals import connection_created
from cockroach.django.introspection import DatabaseIntrospection
from cockroach.django.operations import DatabaseOperations
from cockroach.django.creation import DatabaseCreation

try:
    import psycopg2 as Database
    import psycopg2.extensions
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

class DatabaseWrapper(PostgresDatabaseWrapper):
    vendor = 'cockroachdb'

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.introspection = DatabaseIntrospection(self)
        self.ops = DatabaseOperations(self)
        self.creation = DatabaseCreation(self)

    def _cursor(self):
        new_connection = False
        set_tz = False
        settings_dict = self.settings_dict
        if self.connection is None:
            new_connection = True
            set_tz = settings_dict.get('TIME_ZONE')
            if settings_dict['NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify NAME in your Django settings file.")
            conn_params = {
                'database': settings_dict['NAME'],
            }
            conn_params.update(settings_dict['OPTIONS'])
            if 'autocommit' in conn_params:
                del conn_params['autocommit']
            if settings_dict['USER']:
                conn_params['user'] = settings_dict['USER']
            if settings_dict['PASSWORD']:
                conn_params['password'] = settings_dict['PASSWORD']
            if settings_dict['HOST']:
                conn_params['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                conn_params['port'] = settings_dict['PORT']
            self.connection = Database.connect(**conn_params)
            self.connection.set_client_encoding('UTF8')
            self.connection.set_isolation_level(self.isolation_level)
            connection_created.send(sender=self.__class__, connection=self)
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        if new_connection:
            self.features.uses_savepoints = False
            self.features.can_return_id_from_insert = True
            if set_tz:
                cursor.execute("SET TIME ZONE %s", [settings_dict['TIME_ZONE']])
            """if not hasattr(self, '_version'):
                self.__class__._version = get_version(cursor)
            if self._version[0:2] < (8, 0):
                # No savepoint support for earlier version of PostgreSQL.
                self.features.uses_savepoints = False"""
            """if self.features.uses_autocommit:
                if self._version[0:2] < (8, 2):
                    # FIXME: Needs extra code to do reliable model insert
                    # handling, so we forbid it for now.
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured("You cannot use autocommit=True with PostgreSQL prior to 8.2 at the moment.")
                else:
                    # FIXME: Eventually we're enable this by default for
                    # versions that support it, but, right now, that's hard to
                    # do without breaking other things (#10509).
                    self.features.can_return_id_from_insert = True"""
        return CursorWrapper(cursor)

    def check_constraints(self, table_names=None):
        # Cribbed from django.db.backends.mysql.operations 
        """
        Check each table name in `table_names` for rows with invalid foreign
        key references. This method is intended to be used in conjunction with
        `disable_constraint_checking()` and `enable_constraint_checking()`, to
        determine if rows with invalid references were entered while constraint
        checks were off.
        """
        with self.cursor() as cursor:
            if table_names is None:
                table_names = self.introspection.table_names(cursor)
            for table_name in table_names:
                primary_key_column_name = self.introspection.get_primary_key_column(cursor, table_name)
                if not primary_key_column_name:
                    continue
                key_columns = self.introspection.get_key_columns(cursor, table_name)
                for column_name, referenced_table_name, referenced_column_name in key_columns:
                    cursor.execute(
                        """
                        SELECT REFERRING.`%s`, REFERRING.`%s` FROM `%s` as REFERRING
                        LEFT JOIN `%s` as REFERRED
                        ON (REFERRING.`%s` = REFERRED.`%s`)
                        WHERE REFERRING.`%s` IS NOT NULL AND REFERRED.`%s` IS NULL
                        """ % (
                            primary_key_column_name, column_name, table_name,
                            referenced_table_name, column_name, referenced_column_name,
                            column_name, referenced_column_name,
                        )
                    )
                    for bad_row in cursor.fetchall():
                        raise utils.IntegrityError(
                            "The row in table '%s' with primary key '%s' has an invalid "
                            "foreign key: %s.%s contains a value '%s' that does not "
                            "have a corresponding value in %s.%s."
                            % (
                                table_name, bad_row[0], table_name, column_name,
                                bad_row[1], referenced_table_name, referenced_column_name,
                            )
                        )
