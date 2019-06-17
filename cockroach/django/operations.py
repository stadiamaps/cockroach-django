from django.db.backends.postgresql_psycopg2.base import DatabaseOperations as PostgresDatabaseOperations

class DatabaseOperations(PostgresDatabaseOperations):
   def deferrable_sql(self):
        return ''

   """
   Cockroach does not support returning the last insert ID. 
   Instead Cockroach uses 'RETURNING' as part of the INSERT statement
   to retrieve the ID.
   """
   def last_insert_id(self, cursor, table_name, pk_name):
        pass

   """
   Provides a statement to set the default value for a id column to be a
   unique_rowid()
   """
   def autoinc_sql(self, table, column):
        tbl_name = self.quote_name(table)
        col_name = self.quote_name(column)
        return ["ALTER TABLE %s ALTER COLUMN %s SET DEFAULT unique_rowid()" % \
                (tbl_name, col_name)]
