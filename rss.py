import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# ==========================================
# Database Initialization
# ==========================================
DB_NAME = 'ramdev_super_service.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Client Directory Table
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    client_name TEXT UNIQUE, 
                    contact_info TEXT)''')
    # Daily Parcels Table
    c.execute('''CREATE TABLE IF NOT EXISTS parcels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    date TEXT, 
                    receipt_no INTEGER, 
                    client_name TEXT, 
                    bale_no INTEGER, 
                    weight REAL, 
                    no_of_parcels INTEGER)''')
    # Ledger/Bills Table
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    bill_date TEXT, 
                    client_name TEXT, 
                    total_weight REAL, 
                    applied_rate REAL, 
                    min_amount REAL, 
                    final_bill_amount REAL)''')
    conn.commit()
    conn.close()

# Helper functions to load and save editable data
def load_data(table_name):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(f'SELECT * FROM {table_name}', conn)
    conn.close()
    return df

def save_data(df, table_name):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()

# Initialize the database on startup
init_db()

# ==========================================
# App UI & Layout
# ==========================================
st.set_page_config(page_title="Ramdev Super Service", layout="wide")
st.title("🚚 Ramdev Super Service - Management System")

# Create navigation tabs
tab_parcels, tab_clients, tab_billing, tab_ledger = st.tabs([
    "📦 Daily Parcels", "👥 Client Directory", "🧾 Bill Generator", "📚 Ledger"
])

# ------------------------------------------
# TAB 1: CLIENT DIRECTORY
# ------------------------------------------
with tab_clients:
    st.header("Client Directory")
    
    # Form to add new client
    with st.form("add_client_form", clear_on_submit=True):
        st.subheader("Add New Client")
        c_name = st.text_input("Client Name")
        c_contact = st.text_input("Contact Details / Address")
        submit_client = st.form_submit_button("Save Client")
        
        if submit_client and c_name:
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO clients (client_name, contact_info) VALUES (?, ?)", (c_name, c_contact))
                conn.commit()
                conn.close()
                st.success(f"Client '{c_name}' added successfully!")
            except sqlite3.IntegrityError:
                st.error("A client with this name already exists.")

    st.subheader("Edit / Delete Clients")
    st.info("💡 You can edit or delete data directly in the table below. Changes save automatically.")
    df_clients = load_data('clients')
    # Use data_editor to allow inline editing and deletion
    edited_clients = st.data_editor(df_clients, num_rows="dynamic", use_container_width=True, key="client_editor")
    if st.button("Commit Client Changes"):
        save_data(edited_clients, 'clients')
        st.success("Client directory updated!")

# ------------------------------------------
# TAB 2: DAILY PARCELS
# ------------------------------------------
with tab_parcels:
    st.header("Daily Parcel Data Entry")
    
    # Fetch clients for the dropdown
    df_c = load_data('clients')
    client_list = df_c['client_name'].tolist() if not df_c.empty else ["No clients found. Add a client first."]

    with st.form("add_parcel_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            p_date = st.date_input("Date", date.today())
            p_client = st.selectbox("Client Name", client_list)
            # strictly numbers, step=1 ensures integers
            p_receipt = st.number_input("Receipt No. (Numbers Only)", min_value=0, step=1) 
            
        with col2:
            p_bale = st.number_input("Bale No. (Numbers Only)", min_value=0, step=1)
            p_weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
            p_count = st.number_input("No. of Parcels", min_value=1, step=1)
            
        submit_parcel = st.form_submit_button("Save Parcel Entry")
        
        if submit_parcel and p_client != "No clients found. Add a client first.":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''INSERT INTO parcels (date, receipt_no, client_name, bale_no, weight, no_of_parcels) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (str(p_date), p_receipt, p_client, p_bale, p_weight, p_count))
            conn.commit()
            conn.close()
            st.success(f"Parcel for Receipt #{p_receipt} saved successfully!")

    st.subheader("Edit / Delete Daily Parcels")
    st.info("💡 Edit cells directly or select rows to delete.")
    df_parcels = load_data('parcels')
    edited_parcels = st.data_editor(df_parcels, num_rows="dynamic", use_container_width=True, key="parcel_editor")
    if st.button("Commit Parcel Changes"):
        save_data(edited_parcels, 'parcels')
        st.success("Parcel database updated!")

# ------------------------------------------
# TAB 3: BILL GENERATOR
# ------------------------------------------
with tab_billing:
    st.header("Generate Bill")
    
    col1, col2 = st.columns(2)
    with col1:
        b_client = st.selectbox("Select Client to Bill", client_list, key="bill_client")
        b_rate = st.number_input("Rate per kg (₹)", min_value=0.0, value=10.0, step=0.5)
    with col2:
        b_min_amount = st.number_input("Minimum Bill Amount (₹)", min_value=0.0, value=50.0, step=10.0)
    
    # Show unbilled or all parcels for this client to calculate weight
    df_p = load_data('parcels')
    if not df_p.empty and b_client in client_list:
        client_parcels = df_p[df_p['client_name'] == b_client]
        
        st.write(f"**Parcels on record for {b_client}:**")
        st.dataframe(client_parcels, use_container_width=True)
        
        total_weight = client_parcels['weight'].sum()
        st.write(f"**Total Weight for {b_client}:** {total_weight} kg")
        
        # Calculate Bill
        calculated_amount = total_weight * b_rate
        final_amount = max(calculated_amount, b_min_amount)
        
        st.metric(label="Calculated Amount (Weight × Rate)", value=f"₹{calculated_amount:.2f}")
        st.metric(label="Final Payable Amount (Subject to Minimum)", value=f"₹{final_amount:.2f}")
        
        if st.button("Generate & Save Bill to Ledger"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''INSERT INTO ledger (bill_date, client_name, total_weight, applied_rate, min_amount, final_bill_amount)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (str(date.today()), b_client, total_weight, b_rate, b_min_amount, final_amount))
            conn.commit()
            conn.close()
            st.success(f"Bill of ₹{final_amount:.2f} generated for {b_client} and added to Ledger!")

# ------------------------------------------
# TAB 4: LEDGER
# ------------------------------------------
with tab_ledger:
    st.header("Ledger & Generated Bills")
    st.info("💡 You can edit or delete past bills directly in the table below.")
    
    df_ledger = load_data('ledger')
    edited_ledger = st.data_editor(df_ledger, num_rows="dynamic", use_container_width=True, key="ledger_editor")
    
    if st.button("Commit Ledger Changes"):
        save_data(edited_ledger, 'ledger')
        st.success("Ledger updated!")
        
    # Summary Metrics
    if not edited_ledger.empty:
        st.subheader("Financial Summary")
        total_revenue = edited_ledger['final_bill_amount'].sum()
        st.metric("Total Billed Revenue", f"₹{total_revenue:.2f}")