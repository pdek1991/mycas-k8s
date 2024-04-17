import datetime
import mysql.connector
import schedule
import time

def delete_expired_rows():
    # Connect to the database
    conn = mysql.connector.connect(
        host="mycas-mysql-service",
        user="omi_user",
        password="omi_user",
        database="cas",
    )
    cursor = conn.cursor()

    # Get the current date
    today = datetime.date.today()
    epoch = int(time.time())
    
    # Define the tables to check and delete from
    tables = ['generate_osm', 'entitlements', 'emmg']
    deleted_rows_count = {}

    for table in tables:
        if table == 'generate_osm' or table == 'entitlements':
            # Delete rows where expiry is less than or equal to today's date
            query = f"DELETE FROM {table} WHERE expiry <= %s"
            cursor.execute(query, (today,))
            conn.commit()
            deleted_rows = cursor.rowcount
        elif table == 'emmg':
            # Delete rows where endtime is less than or equal to the current epoch timestamp
            query = f"DELETE FROM {table} WHERE endtime <= %s"
            cursor.execute(query, (epoch,))
            conn.commit()
            deleted_rows = cursor.rowcount

        # Store the count in the dictionary
        deleted_rows_count[table] = deleted_rows
        print(f"Deleted {deleted_rows} rows from table {table}")

    # Close the database connection
    cursor.close()
    conn.close()

    # Return the deleted rows count
    return deleted_rows_count

# Schedule the delete_expired_rows() function to run every day at 00:00 hours
schedule.every().day.at("00:00").do(delete_expired_rows)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
