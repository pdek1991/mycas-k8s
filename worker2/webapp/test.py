import mysql.connector.pooling

# MySQL database configuration
db_config = {
    'host': 'mycas-mysql-service',
    'user': 'omi_user',
    'password': 'omi_user',
    'database': 'cas'
}

# Create MySQL connection pool
connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=15,
    pool_reset_session=True,
    **db_config
)

# Your application code that uses the connection pool goes here...

# Release all connections from the connection pool
while True:
    try:
        connection = connection_pool.get_connection()
        if connection:
            connection.close()
        else:
            break
    except mysql.connector.Error:
        break
