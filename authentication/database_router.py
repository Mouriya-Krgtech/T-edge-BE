class ReadOnlyLicenceKeysRouter:
    def db_for_read(self, model, **hints):
        """Direct read operations for specific models to the 'licence_keys' database."""
        if model._meta.app_label == 'licence':
            print(f"📖 Read request for {model} -> Using 'licence_keys' database")
            return 'licence_keys'
        return None

    def db_for_write(self, model, **hints):
        """Block write operations to the 'licence_keys' database."""
        if model._meta.app_label == 'licence':
            print(f"❌ Write request blocked for {model}")
            return 'default'  # Redirect writes to the default database or block them.
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations only if they are within the same database."""
        db_set = {'default', 'licence_keys'}
        if {obj1._state.db, obj2._state.db} <= db_set:
            print(f"✅ Relation allowed between {obj1} and {obj2}")
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Prevent migrations on the 'licence_keys' database."""
        if app_label == 'licence':
            print(f"🚫 Migration blocked for app: {app_label} on db: {db}")
            return False  # Block migrations for the licence app.
        return None
