import psycopg2
import time
import json
import paho.mqtt.client as mqtt
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from Controller import Contoller


DATABASE = "access_log_database"
DEFAULT_DB = "postgres"
DATABASE_USER = "pi"
DATABASE_PASS = "123"
BROKER = "broker.hivemq.com"
PORT = 1883

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(21, GPIO.OUT)

doorOpen = True

def get_db_connection():
    conn = psycopg2.connect(
        dbname = DATABASE,
        user = DATABASE_USER,
        password = DATABASE_PASS,
        host = "localhost",
        port = "5432"
    )
    return conn

def create_database():
    try:
        conn = psycopg2.connect(f"user={DATABASE_USER} password={DATABASE_PASS} dbname={DEFAULT_DB}")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(f"CREATE DATABASE {DATABASE}")

        print("Database created successfully")

    # Create database if not exists
    except (Exception, psycopg2.DatabaseError) as error: 
        print("Error when creating database", error)

    finally:
        if conn is not None:
            cur.close()
            conn.close()

def create_log_table():
    command = ("""
        CREATE TABLE logs (
            id SERIAL PRIMARY KEY,
            chamber_id VARCHAR,
            time_open TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            time_close TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    insert_to_database(command,"CREATE")

def insert_to_database(command,operation):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(command)
        conn.commit()

        if operation == "QUERY":
            rows = cur.fetchall()
            return rows
        print("Success")
        
    except(Exception, psycopg2.DatabaseError) as error:
        print("Error executing SQL command \n" + command)
        print(error)
    finally:
        if conn is not None:
            cur.close()
            conn.close()

def openCrate():
    global doorOpen
    timestamp_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Open crate sum
    chamber_id = str(input("Which chamber"))
    while doorOpen:
        doorOpen = input("Still open? t/f >")
    timeclose_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    command = f"INSERT INTO logs (chamber_id,time_open, time_close) values ('{chamber_id}', '{timestamp_val}','{timeclose_val}')"
    insert_to_database(command,"INSERT")

def check_if_item_inside():
    print("===Door unlocked===")
    doorOpen = True
    message = None
    previous_message = None
    while doorOpen:
        distance = controller.read_ultrasonic()
        print(distance)
        if distance <= 28.4:
            print("Occupied")
            # print("====Door locked===")
            message = "Occupied"
            GPIO.output(21, False)
        else:
            print("vacant")
            message = "Vacant"
            GPIO.output(21, True)

        if previous_message != message:
            client.publish("GuardianBox/sonic-1-status", message)

        previous_message = message
        
def get_logs():
    command =  f"SELECT * from logs"
    rows = insert_to_database(command, "QUERY")
    data = {}
    for row in rows:
        data = {
            "id" : row[0],
            "chamber_id" : row[1],
            "time_open" : row[2].strftime("%d-%m-%Y %H:%M:%S"),
            "time_close" : row[3].strftime("%d-%m-%Y %H:%M:%S")
        }
        
        print(data)
    # print(rows)
    client.publish("GuardianBox/logs-database", "2")

    


light_led = 4
ultra_pin = 17
echo_pin = 27

controller = Contoller(light_led,ultra_pin,echo_pin)

def on_message(client, usrdata, message):
    print("Receive : " + str(message.payload.decode()) + "\n")
    if(message.payload.decode() == "0"):
        # client.publish("GuardianBox/SonicSta", "0")
        client.publish("Magna/LampSta", "0")
        GPIO.output(21, False)
    else:
        client.publish("Magna/LampSta", "1")
        GPIO.output(21, True)
        # client.publish("GuardianBox/SonicSta", "1")


def on_connect(client, usrdata, flags, rc):
    if rc == 0:
        print("Successfully Connected")
    else:
        print("Error")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message


client.connect(BROKER, PORT)
# client.subscribe("GuardianBox/SonicCmd", 0)
client.subscribe("Magna/LampCmd", 0)

opt = None
while opt != 0:
    client.loop_start()
    # client.publish("GuardianBox/SonicSta", "hehe")
    if opt == 1:
        create_database()
    elif opt == 2:
        create_log_table()
    elif opt == 3:
        openCrate()
    elif opt == 4:
        controller.turn_on()
    elif opt == 5:
        controller.turn_off()
    elif opt == 6:
        check_if_item_inside()
    elif opt == 7:
        get_logs()
    client.loop_stop()
    opt = int(input("Menu: \n0.Exit\n1.Create DB \n2.Create Table\n3.Open Crate \n4.Turn on light \n5.Turn off light \n> "))
# client.loop_forever()