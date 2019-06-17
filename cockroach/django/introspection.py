from django.db.backends import BaseDatabaseIntrospection


class DatabaseIntrospection(BaseDatabaseIntrospection):
    def get_table_list(self, cursor):
        cursor.execute("SHOW TABLES")
        # The second TableInfo field is 't' for table or 'v' for view.
        return [row[0] for row in cursor.fetchall()]
