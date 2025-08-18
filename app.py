import os
import tkinter as tk
from tkinter import messagebox
import random
import time
import geocoder
from twilio.rest import Client
import serial
import pandas as pd
from scipy.stats import zscore
import streamlit as st 

# Twilio credentials 
account_sid = ''
auth_token = ''
twilio_number = '+'
client = Client(account_sid, auth_token)

# Load dataset safely
file_path = "patient_finaldataset.csv"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"Dataset file not found at: {file_path}")
df = pd.read_csv(file_path)


def detect_anomalies(df):
    columns_to_check = ['heart_rate', 'spo2', 'temperature', 'respiratory_rate']

    
    for col in columns_to_check:
        df[f'z_score_{col}'] = zscore(df[col])

   
    anomaly_conditions = (
        (df['z_score_heart_rate'].abs() > 3) |
        (df['z_score_spo2'].abs() > 3) |
        (df['z_score_temperature'].abs() > 3) |
        (df['z_score_respiratory_rate'].abs() > 3)
    )

    df['is_abnormal'] = anomaly_conditions
    return df


patient_data_analyzed = detect_anomalies(df)


st.write("Abnormal Data Detected: ", patient_data_analyzed[patient_data_analyzed['is_abnormal'] == True])


def is_abnormal(df):
    return df['is_abnormal'].any()

# Contacts for each patient
contacts = {
    1: {
        'doctor_phone': '+91',
        'emergency_contact_1': '+919',
        'emergency_contact_2': '+91',
    },
    2: {
        'doctor_phone': '+91',
        'emergency_contact_1': '+91',
        'emergency_contact_2': '+91',
    }
}

# Function to send SMS to doctor
def send_alert_to_doctor(patient_id, alerts, contact):
    doctor_msg = f"ALERT: Patient {patient_id} has abnormal readings. Details: {', '.join(alerts)}"
    try:
        message = client.messages.create(
            body=doctor_msg,
            from_=twilio_number,
            to=contact['doctor_phone']
        )
        st.write(f"Alert sent to Doctor: {contact['doctor_phone']}")
    except Exception as e:
        st.error(f"Error sending alert to doctor: {e}")

# Function to handle user interaction for alerts
def handle_patient_interaction(patient_id, contact, alerts):
    st.info(f"Patient {patient_id}: Are you alright?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Yes 👍", key=f"yes_{patient_id}"):
            st.write("Patient confirmed they are alright.")
    with col2:
        if st.button(f"No ❌", key=f"no_{patient_id}"):
            st.write("Patient declined. Sending alert to doctor.")
            send_alert_to_doctor(patient_id, alerts, contact)
            
            try:
                client.calls.create(
                    to=contact['emergency_contact_1'],
                    from_=twilio_number,
                   # url="http://demo.twilio.com/docs/voice.xml"
                )
                st.success(f"Emergency contact 1 ({contact['emergency_contact_1']}) has been notified.")
            except Exception as e:
                st.error(f"Error calling emergency contact 1: {e}")

            try:
                client.calls.create(
                    to=contact['emergency_contact_2'],
                    from_=twilio_number,
                   # url="http://demo.twilio.com/docs/voice.xml"
                )
                st.success(f"Emergency contact 2 ({contact['emergency_contact_2']}) has been notified.")
            except Exception as e:
                st.error(f"Error calling emergency contact 2: {e}")

            # Call ambulance
            try:
                client.calls.create(
                    to="+91",  # Placeholder for ambulance phone number
                    from_=twilio_number,
                    #url="http://your_location_api_or_file.com/location.xml"
                )
                st.success("Ambulance has been called and location shared.")
            except Exception as e:
                st.error(f"Error calling ambulance: {e}")


st.title("🩺 Patient Health Monitoring Dashboard")


for patient_id in patient_data_analyzed['patient_id'].unique():
    patient_data = patient_data_analyzed[patient_data_analyzed['patient_id'] == patient_id]
    latest = patient_data.iloc[-1]

    alerts = []
    if latest['z_score_heart_rate'] > 3 or latest['z_score_heart_rate'] < -3:
        alerts.append("Abnormal Heart Rate")
    if latest['z_score_spo2'] > 3 or latest['z_score_spo2'] < -3:
        alerts.append("Abnormal SpO2 Level")
    if latest['z_score_temperature'] > 3 or latest['z_score_temperature'] < -3:
        alerts.append("Abnormal Temperature")
    if latest['z_score_respiratory_rate'] > 3 or latest['z_score_respiratory_rate'] < -3:
        alerts.append("Abnormal Respiratory Rate")

    if alerts:
        contact = contacts.get(patient_id, None)
        if contact:
            st.subheader(f"🚨 Patient {patient_id} - ALERT DETECTED")
            st.write(f"Vitals at {latest['timestamp']}:")
            st.write(", ".join(alerts))

            st.line_chart(patient_data[['heart_rate']].set_index(patient_data['timestamp']))

            send_alert_to_doctor(patient_id, alerts, contact)
            handle_patient_interaction(patient_id, contact, alerts)

            st.markdown("---")

def get_gps_location():
    try:
        ser = serial.Serial('COM3', 4800, timeout=1)  # Adjust COM port if needed
        while True:
            line = ser.readline().decode('ascii', errors='replace')
            if line.startswith('$GPGGA'):
                parts = line.split(',')
                if len(parts) > 5:
                    lat = float(parts[2]) / 100
                    lon = float(parts[4]) / 100
                    return lat, lon
    except Exception as e:
        print(f"GPS error: {e}")

