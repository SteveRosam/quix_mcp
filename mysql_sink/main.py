import mysql.connector
from mysql.connector import Error
from quixstreams import Application
from quixstreams.sinks import BatchingSink, SinkBatch, SinkBackpressureError
import json
import os
import time

class MySQLSink(BatchingSink):
    def __init__(self, host, database, user, password):
        super().__init__()
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.table_name = None
        self.columns = None

    def _connect_to_mysql(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False

    def _create_table(self, data):
        if not self._connect_to_mysql():
            return False

        try:
            cursor = self.connection.cursor()
            
            # Get the first message to determine the data structure
            sample_data = json.loads(data[0])
            self.columns = sample_data.keys()
            
            # Create table name based on topic
            self.table_name = f"kafka_{int(time.time())}"
            
            # Create table with appropriate data types
            columns_sql = []
            for col in self.columns:
                # Determine appropriate MySQL data type based on first value
                value = sample_data[col]
                if isinstance(value, int):
                    columns_sql.append(f"{col} BIGINT")
                elif isinstance(value, float):
                    columns_sql.append(f"{col} DOUBLE")
                elif isinstance(value, bool):
                    columns_sql.append(f"{col} BOOLEAN")
                else:
                    columns_sql.append(f"{col} VARCHAR(255)")
            
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {self.table_name} (" + \
                             ", ".join(columns_sql) + \
                             ", id INT AUTO_INCREMENT PRIMARY KEY)"
            
            cursor.execute(create_table_sql)
            self.connection.commit()
            print(f"Created table: {self.table_name}")
            return True
        except Error as e:
            print(f"Error creating table: {e}")
            return False

    def _write_to_mysql(self, data):
        if not self.table_name:
            if not self._create_table(data):
                return False

        try:
            cursor = self.connection.cursor()
            
            # Prepare INSERT statement
            placeholders = ", ".join("%s" for _ in self.columns)
            columns = ", ".join(self.columns)
            insert_sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            
            # Convert all data to tuples
            values = []
            for item in data:
                record = json.loads(item)
                row_values = tuple(record[col] for col in self.columns)
                values.append(row_values)
            
            # Execute batch insert
            cursor.executemany(insert_sql, values)
            self.connection.commit()
            print(f"Inserted {len(values)} records into {self.table_name}")
            return True
        except Error as e:
            print(f"Error writing to MySQL: {e}")
            return False

    def write(self, batch: SinkBatch):
        attempts_remaining = 3
        data = [item.value for item in batch]
        
        while attempts_remaining:
            try:
                return self._write_to_mysql(data)
            except ConnectionError:
                attempts_remaining -= 1
                if attempts_remaining:
                    time.sleep(3)
            except TimeoutError:
                raise SinkBackpressureError(
                    retry_after=30.0,
                    topic=batch.topic,
                    partition=batch.partition,
                )
        raise Exception("Error while writing to MySQL")

def main():
    # MySQL connection details
    mysql_config = {
        "host": os.environ["mysql_server"],
        "database": os.environ["mysql_db"],
        "user": os.environ["mysql_user"],
        "password": os.environ["mysql_password"]
    }

    # Setup Quix Streams Application
    app = Application(
        consumer_group="mysql_sink",
        auto_create_topics=True,
        auto_offset_reset="earliest"
    )

    # Create MySQL sink
    mysql_sink = MySQLSink(**mysql_config)
    
    # Get the input topic from environment variable
    input_topic = app.topic(name=os.getenv("KAFKA_TOPIC", "default_topic"))
    sdf = app.dataframe(topic=input_topic)
    
    # Process the data
    sdf = sdf.apply(lambda row: row).print(metadata=True)
    
    # Set up the sink
    sdf.sink(mysql_sink)
    
    # Run the application
    app.run()

if __name__ == "__main__":
    main()
