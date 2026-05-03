import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import datetime
import streamlit.components.v1 as components

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
                    client_gstin TEXT,
                    address TEXT,
                    phone TEXT)''')
    # Daily Parcels Table 
    c.execute('''CREATE TABLE IF NOT EXISTS parcels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    date TEXT, 
                    receipt_no INTEGER, 
                    client_name TEXT, 
                    destination TEXT,
                    bale_no INTEGER, 
                    weight REAL, 
                    no_of_parcels INTEGER)''')
    # Ledger/Bills Table
    c.execute('''CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    invoice_no TEXT,
                    bill_date TEXT, 
                    billing_month TEXT,
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

init_db()

# ==========================================
# App UI & Layout
# ==========================================
st.set_page_config(page_title="Ramdev Super Service", layout="wide")
st.title("🚚 Ramdev Super Service - Management System")

tab_parcels, tab_clients, tab_billing, tab_ledger = st.tabs([
    "📦 Daily Parcels", "👥 Client Directory", "🧾 Bill Generator", "📚 Ledger"
])

# ------------------------------------------
# TAB 1: CLIENT DIRECTORY
# ------------------------------------------
with tab_clients:
    st.header("Client Directory")
    
    with st.form("add_client_form", clear_on_submit=True):
        st.subheader("Add New Client")
        c_name = st.text_input("Client Name")
        c_gstin = st.text_input("Client GSTIN")
        c_address = st.text_area("Address")
        c_phone = st.text_input("Phone Number")
        submit_client = st.form_submit_button("Save Client")
        
        if submit_client and c_name:
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO clients (client_name, client_gstin, address, phone) VALUES (?, ?, ?, ?)", 
                          (c_name, c_gstin, c_address, c_phone))
                conn.commit()
                conn.close()
                st.success(f"Client '{c_name}' added successfully!")
            except sqlite3.IntegrityError:
                st.error("A client with this name already exists.")

    st.subheader("Edit / Delete Clients")
    df_clients = load_data('clients')
    edited_clients = st.data_editor(df_clients, num_rows="dynamic", use_container_width=True, key="client_editor")
    if st.button("Commit Client Changes"):
        save_data(edited_clients, 'clients')
        st.success("Client directory updated!")

# ------------------------------------------
# TAB 2: DAILY PARCELS
# ------------------------------------------
with tab_parcels:
    st.header("Daily Parcel Data Entry")
    
    df_c = load_data('clients')
    client_list = df_c['client_name'].tolist() if not df_c.empty else ["No clients found."]

    with st.form("add_parcel_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("Date", date.today())
            p_client = st.selectbox("Client Name", client_list)
            p_receipt = st.number_input("Receipt No. (Numbers Only)", min_value=0, step=1) 
            p_dest = st.text_input("Destination (Dest)")
        with col2:
            p_bale = st.number_input("Bale No. (Numbers Only)", min_value=0, step=1)
            p_weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
            p_count = st.number_input("No. of Parcels", min_value=1, step=1)
            
        submit_parcel = st.form_submit_button("Save Parcel Entry")
        
        if submit_parcel and p_client != "No clients found.":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # Duplicate check logic
            c.execute("SELECT 1 FROM parcels WHERE receipt_no = ?", (p_receipt,))
            exists = c.fetchone()
            
            if exists:
                st.error(f"⚠️ Error: Receipt No. {p_receipt} has already been used!")
            else:
                c.execute('''INSERT INTO parcels (date, receipt_no, client_name, destination, bale_no, weight, no_of_parcels) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (str(p_date), p_receipt, p_client, p_dest, p_bale, p_weight, p_count))
                conn.commit()
                st.success(f"✅ Parcel for Receipt #{p_receipt} saved!")
            conn.close()

    st.subheader("Edit / Delete Daily Parcels")
    df_parcels = load_data('parcels')
    edited_parcels = st.data_editor(df_parcels, num_rows="dynamic", use_container_width=True, key="parcel_editor")
    if st.button("Commit Parcel Changes"):
        save_data(edited_parcels, 'parcels')
        st.success("Parcel database updated!")

# ------------------------------------------
# TAB 3: BILL GENERATOR
# ------------------------------------------
with tab_billing:
    st.header("Generate Monthly Invoice")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        b_client = st.selectbox("Select Client", client_list, key="bill_client")
        b_rate = st.number_input("Rate per kg (₹)", min_value=0.0, value=10.0, step=0.5)
    with col2:
        b_min_amount = st.number_input("Total Minimum Bill Amount (₹)", min_value=0.0, value=50.0, step=10.0)
    with col3:
        b_month = st.selectbox("Billing Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        b_year = st.selectbox("Billing Year", [str(y) for y in range(2024, 2030)], index=2)
    
    df_p = load_data('parcels')
    df_c = load_data('clients')
    
    if not df_p.empty and b_client in client_list:
        client_parcels = df_p[df_p['client_name'] == b_client]
        
        total_weight = client_parcels['weight'].sum()
        
        # Calculate Bill (Handles the Weight vs Minimum logic automatically)
        calculated_amount = total_weight * b_rate
        final_amount = max(calculated_amount, b_min_amount)
        
        st.write("---")
        
        # Display calculation alerts to the user
        if calculated_amount > b_min_amount:
            st.success(f"⚖️ **Weight amount (₹{calculated_amount:.2f}) exceeded the minimum.** Charging by weight.")
        else:
            st.warning(f"🛡️ **Weight amount (₹{calculated_amount:.2f}) was too low.** Applying Minimum Bill Amount.")
            
        st.metric(label="Final Payable Amount", value=f"₹{final_amount:.2f}")
        
        if st.button("Generate & Display Bill"):
            # Fetch Client Details
            client_info = df_c[df_c['client_name'] == b_client].iloc[0]
            c_gst = client_info['client_gstin'] if client_info['client_gstin'] else "N/A"
            c_add = client_info['address'] if client_info['address'] else "N/A"
            c_ph = client_info['phone'] if client_info['phone'] else "N/A"
            
            # Generate Invoice Number
            inv_no = f"RSS/{b_year}/{datetime.datetime.now().strftime('%m%d%H%M')}"
            current_date = date.today().strftime("%d-%m-%Y")
            
            # Build Table Rows for Invoice
            table_rows = ""
            for index, row in client_parcels.iterrows():
                row_amt = row['weight'] * b_rate
                table_rows += f"""
                <tr>
                    <td style='border: 1px solid black; padding: 5px; text-align: center;'>{row['date']}</td>
                    <td style='border: 1px solid black; padding: 5px; text-align: center;'>{row['receipt_no']}</td>
                    <td style='border: 1px solid black; padding: 5px; text-align: center;'>{row['destination']}</td>
                    <td style='border: 1px solid black; padding: 5px; text-align: center;'>{row['weight']}</td>
                    <td style='border: 1px solid black; padding: 5px; text-align: center;'>{row_amt:.2f}</td>
                </tr>
                """
            
            # Construct the HTML Layout
            invoice_html = f"""
            <div style="background-color: white; color: black; padding: 30px; border: 2px solid black; font-family: Arial, sans-serif; max-width: 800px; margin: auto;">
                
                <h1 style="text-align: center; margin: 0; font-size: 28px; font-weight: bold;">RAMDEV SUPER SERVICE</h1>
                <p style="text-align: center; margin: 5px 0 0 0; font-size: 14px;">
                    53/54, dulanbi kasam chawl, S.L Matkar Marg, Prabhadevi-400025<br>
                    <strong>GSTIN: 27ADPPR2190E1ZA</strong>
                </p>
                
                <h3 style="text-align: center; text-decoration: underline; margin-top: 15px; margin-bottom: 25px;">MONTHLY INVOICE</h3>
                
                <table style="width: 100%; margin-bottom: 20px; font-size: 14px; border: none;">
                    <tr>
                        <td style="width: 60%; vertical-align: top;">
                            <strong>Billed To:</strong><br>
                            Client Name: <strong>{b_client}</strong><br>
                            Client GSTIN: {c_gst}<br>
                            Address: {c_add}<br>
                            Phone: {c_ph}
                        </td>
                        <td style="width: 40%; vertical-align: top; text-align: right;">
                            <strong>Invoice No:</strong> {inv_no}<br>
                            <strong>Date:</strong> {current_date}<br>
                            <strong>Billing Month:</strong> {b_month} / {b_year}
                        </td>
                    </tr>
                </table>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid black; padding: 8px;">Date</th>
                        <th style="border: 1px solid black; padding: 8px;">LR No.</th>
                        <th style="border: 1px solid black; padding: 8px;">Dest</th>
                        <th style="border: 1px solid black; padding: 8px;">Weight</th>
                        <th style="border: 1px solid black; padding: 8px;">Amt (₹)</th>
                    </tr>
                    {table_rows}
                    <tr>
                        <th colspan="3" style="text-align: right; border: 1px solid black; padding: 8px;">Total Weight:</th>
                        <th style="border: 1px solid black; padding: 8px; text-align: center;">{total_weight:.2f}</th>
                        <th style="border: 1px solid black; padding: 8px;"></th>
                    </tr>
                    <tr>
                        <th colspan="4" style="text-align: right; border: 1px solid black; padding: 8px;">Total Minimum Applicable:</th>
                        <th style="border: 1px solid black; padding: 8px; text-align: center;">{b_min_amount:.2f}</th>
                    </tr>
                    <tr>
                        <th colspan="4" style="text-align: right; border: 1px solid black; padding: 8px; font-size: 16px;">Total Amount:</th>
                        <th style="border: 1px solid black; padding: 8px; font-size: 16px; text-align: center;">₹ {final_amount:.2f}</th>
                    </tr>
                </table>
                
                <table style="width: 100%; font-size: 14px; border: none; margin-top: 30px;">
                    <tr>
                        <td style="width: 60%; vertical-align: bottom;">
                            <strong>Bank Details for Payment:</strong><br>
                            Bank Name: Bharat co-operative Bank Ltd.<br>
                            Branch: Vasai Branch<br>
                            Account No: 002412100017543<br>
                            IFSC Code: BCBM0000025
                        </td>
                        <td style="width: 40%; text-align: right; vertical-align: bottom;">
                            <br><br><br><br>
                            _________________________<br>
                            <strong>Authorized Signatory</strong>
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            # Display the Invoice Layout correctly using the HTML component
            components.html(invoice_html, height=800, scrolling=True)
            
            # Save to Ledger
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''INSERT INTO ledger (invoice_no, bill_date, billing_month, client_name, total_weight, applied_rate, min_amount, final_bill_amount)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (inv_no, current_date, f"{b_month} {b_year}", b_client, total_weight, b_rate, b_min_amount, final_amount))
            conn.commit()
            conn.close()
            
            st.success("✅ Bill Generated, saved to Ledger, and ready for printing!")
            st.info("🖨️ **How to Print/Save as PDF:** Right-click the invoice and select 'Print' or press `Ctrl + P` to save this layout as a PDF.")

# ------------------------------------------
# TAB 4: LEDGER
# ------------------------------------------
with tab_ledger:
    st.header("Ledger & Generated Bills")
    
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
