"Unit tests for the test-database guard function (no database required)."
import pytest
from tests.conftest import validate_test_database_url

class TestValidateTestDatabaseUrl:
    "Tests fir validate_test_database_url()."
    def test_heimdall_rejected(self):
        "Database named 'heimdall' is rejected (does not end with '_test')."
        with pytest.raises(RuntimeError, match="Refusing to run tests on non-test database: heimdall"):
            validate_test_database_url("postgresql://user:pass@localhost:5432/heimdall")

    def test_heimdall_test_accepted(self):
        "Database named 'heimdall_test' is accepted (ends with '_test')."
        # Should not raise an exception
        validate_test_database_url("postgresql://user:pass@localhost:5432/heimdall_test")
        #If we reach here, there is no exception.

    def test_heimdall_notest_rejected(self):
        """Database named 'heimdall_notest' (does not end with _test) is rejected."""
        with pytest.raises(RuntimeError, match="Refusing to run tests on non-test database: heimdall_notest"):
            validate_test_database_url("postgresql://user:pass@localhost:5432/heimdall_notest")

    def test_no_database_name_rejected(self):
        """URL with no database name (empty path) is rejected."""
        with pytest.raises(RuntimeError, match="TEST_DATABASE_URL has no database name"):
            validate_test_database_url("postgresql://user:pass@localhost:5432/")

    def test_none_url_rejected(self):
        """None URL is rejected."""
        with pytest.raises(RuntimeError, match="TEST_DATABASE_URL not set"):
            validate_test_database_url(None)

    def test_empty_string_rejected(self):
        """Empty string URL is rejected."""
        with pytest.raises(RuntimeError, match="TEST_DATABASE_URL not set"):
            validate_test_database_url("")

    def test_heimdall_test_with_query_params_accepted(self):
        """Database name with query parameters still works."""
        validate_test_database_url("postgresql://user:pass@localhost:5432/heimdall_test?sslmode=require")

    def test_heimdall_test_with_port_and_path_accepted(self):
        """Full URL with port and path works."""
        validate_test_database_url("postgresql://user:pass@localhost:5433/heimdall_test")