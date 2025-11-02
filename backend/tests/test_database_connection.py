import pytest
from unittest.mock import patch, MagicMock

# run with: pytest backend/tests/test_database_connection.py
# Mock the settings before they are imported by the models module
@pytest.fixture(autouse=True)
def mock_settings_before_import():
    with patch.dict('sys.modules', {
        'app.config': MagicMock(
            settings=MagicMock(
                db_type='mysql',
                get_database_url=lambda: 'mysql+pymysql://user:pass@host:3306/db'
            )
        )
    }) as sys_modules_mock:
        # After patching sys.modules, we need to make sure that when 'app.models' is imported,
        # it gets the patched version of 'app.config'.
        # If 'app.models' was already imported, we might need to reload it.
        if 'app.models' in sys.modules:
            import importlib
            import app.models
            importlib.reload(app.models)
        yield sys_modules_mock

# Since create_engine is a function, we patch it in the module where it is used.
@patch('app.models.create_engine')
def test_mysql_engine_uses_pool_recycle(mock_create_engine):
    # We need to trigger the code that calls create_engine.
    # In this case, simply importing the module will execute the top-level statements.
    import app.models

    # Now, we can assert that create_engine was called with the correct arguments
    mock_create_engine.assert_called_once_with(
        'mysql+pymysql://user:pass@host:3306/db',
        pool_recycle=3600
    )
