"""Use PyMySQL as a drop-in for mysqlclient (pure Python, no system MySQL headers)."""

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass
