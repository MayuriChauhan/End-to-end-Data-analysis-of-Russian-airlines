import streamlit as st
import pandas as pd
import sqlite3

# Function to fetch aircraft codes from SQLite database
def fetch_aircraft_codes():
    conn = sqlite3.connect('travel.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT aircraft_code FROM flights")
    data = cursor.fetchall()
    conn.close()
    return [row[0] for row in data]

# Function to fetch data for selected aircraft from SQLite database
def fetch_data(selected_aircraft):
    conn = sqlite3.connect('travel.sqlite')
    cursor = conn.cursor()

    # Fetch aircraft data
    cursor.execute(f"""
        SELECT model->>'en', "range"
        FROM aircrafts_data
        WHERE aircraft_code = '{selected_aircraft}'
    """)
    aircraft_data = cursor.fetchone()

    # Fetch flight data
    cursor.execute(f"""
        SELECT COUNT(*) AS total_flights
        FROM flights
        WHERE aircraft_code = '{selected_aircraft}'
    """)
    flight_data = cursor.fetchone()

    # Fetch booking data
    cursor.execute(f"""
        SELECT COUNT(*) AS total_bookings,
               SUM(total_amount) AS total_revenue
        FROM bookings
        WHERE book_ref IN (
            SELECT DISTINCT book_ref
            FROM tickets
            WHERE ticket_no IN (
                SELECT ticket_no
                FROM ticket_flights
                WHERE flight_id IN (
                    SELECT flight_id
                    FROM flights
                    WHERE aircraft_code = '{selected_aircraft}'
                )
            )
        )
    """)
    booking_data = cursor.fetchone()

    # Calculate occupancy rate and revenue after increasing occupancy rate by 10%
    cursor.execute(f"""
        SELECT AVG(a.seats_count) / b.num_seats as occupancy_rate
        FROM (
            SELECT COUNT(*) as seats_count
            FROM boarding_passes
            INNER JOIN flights 
            ON boarding_passes.flight_id=flights.flight_id
            WHERE flights.aircraft_code = '{selected_aircraft}'
            GROUP BY flights.flight_id
        ) as a 
        INNER JOIN (
            SELECT COUNT(*) as num_seats 
            FROM seats 
            WHERE aircraft_code = '{selected_aircraft}'
        ) as b 
        ON 1=1
    """)
    occupancy_data = cursor.fetchone()

    # Calculate revenue after increasing occupancy rate by 10%
    if occupancy_data[0]:
        increased_occupancy_rate = min(1, occupancy_data[0] + 0.1)
        increased_revenue = booking_data[1] * (increased_occupancy_rate / occupancy_data[0])
    else:
        increased_revenue = None

    conn.close()

    return aircraft_data, flight_data, booking_data, occupancy_data, increased_revenue

# Streamlit web application
st.set_page_config(layout="wide")

st.title('Aircrafts Analysis Results')
st.write('Data fetched from travel.sqlite database')

# Fetch aircraft codes
aircraft_codes = fetch_aircraft_codes()

# Dropdown list to select aircraft
selected_aircraft = st.selectbox('Select Aircraft:', aircraft_codes)

# Fetch data for selected aircraft
aircraft_data, flight_data, booking_data, occupancy_data, increased_revenue_data = fetch_data(selected_aircraft)

# Display information for selected aircraft
if aircraft_data:
    st.subheader(f'Data for Aircraft Code: {selected_aircraft}')

    # Aircraft data
    st.info('**Aircraft Data:**')
    st.write(f'Model: {aircraft_data[0]}')
    st.write(f'Range: {aircraft_data[1]}')

    # Other data
    st.info('**Flight Data:**')
    st.write(f'Total Flights: {flight_data[0]}')

    st.info('**Booking Data:**')
    st.write(f'Total Bookings: {booking_data[0]}')
    st.write(f'Total Revenue: ${booking_data[1]:,.2f}')

    if occupancy_data[0]:
        st.info('**Occupancy Rate:**')
        st.write(f'{occupancy_data[0]*100:.2f}%')

        if increased_revenue_data is not None:
            st.info('**Revenue after increasing occupancy rate by 10%:**')
            st.write(f'${increased_revenue_data:,.2f}')
        else:
            st.info('**Revenue after increasing occupancy rate by 10%:**')
            st.write('N/A (No occupancy data available for calculation)')

    else:
        st.warning('No occupancy data available for the selected aircraft code.')

else:
    st.warning('No data available for the selected aircraft code.')
