import os
from kivy.config import Config
# This disables the "Red Dot" right-click simulation
Config.set('input', 'mouse', 'mouse,disable_multitouch')

# ... rest of your imports (kivymd, sqlite3, etc.) go here ...
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.list import ThreeLineAvatarIconListItem, TwoLineListItem, IconLeftWidget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
import sqlite3
from datetime import datetime

# --- 1. The Layout (User Interface) ---
KV = '''
MDBoxLayout:
    orientation: 'vertical'

    MDTopAppBar:
        id: top_bar
        title: "Gurudwara Donation Tracker"
        elevation: 4
        # The 'left_action_items' will change dynamically based on the screen
        right_action_items: [["cash-plus", lambda x: app.show_period_dialog()]]

    MDScreenManager:
        id: screen_manager

        # --- SCREEN 1: THE LIST OF FAMILIES ---
        MDScreen:
            name: "home_screen"
            
            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                spacing: "10dp"

                MDTextField:
                    id: search_field
                    hint_text: "Search Family Name..."
                    mode: "rectangle"
                    on_text: app.filter_list(self.text)

                ScrollView:
                    MDList:
                        id: container

            MDFloatingActionButton:
                icon: "account-plus"
                pos_hint: {"center_x": .9, "center_y": .1}
                elevation: 0
                on_release: app.show_add_dialog()

        # --- SCREEN 2: FAMILY DETAIL & HISTORY ---
        MDScreen:
            name: "detail_screen"
            on_enter: app.load_history()

            MDBoxLayout:
                orientation: 'vertical'
                padding: "10dp"
                
                # Header Info
                MDCard:
                    size_hint_y: None
                    height: "100dp"
                    padding: "10dp"
                    orientation: "vertical"
                    elevation: 2
                    
                    MDLabel:
                        id: detail_name
                        text: "Family Name"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        halign: "center"
                    
                    MDLabel:
                        id: detail_land
                        text: "Land: 0 Acres"
                        theme_text_color: "Secondary"
                        halign: "center"

                    MDLabel:
                        id: detail_balance
                        text: "Due: ₹0"
                        theme_text_color: "Error"
                        font_style: "H5"
                        halign: "center"
                
                MDLabel:
                    text: "Transaction History"
                    size_hint_y: None
                    height: "40dp"
                    padding: ["10dp", "10dp"]
                    font_style: "Subtitle2"
                    theme_text_color: "Primary"

                # History List
                ScrollView:
                    MDList:
                        id: history_container

            # Button to Add Payment for this specific family
            MDFloatingActionButton:
                icon: "cash-check"
                pos_hint: {"center_x": .9, "center_y": .1}
                md_bg_color: app.theme_cls.primary_color
                on_release: app.show_payment_dialog()
'''

# --- 2. Custom List Items ---
class FamilyItem(ThreeLineAvatarIconListItem):
    family_id = StringProperty()

class TransactionItem(TwoLineListItem):
    pass

class DonationApp(MDApp):
    dialog = None
    current_family_id = None # Tracks which family we are looking at

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.db_init()
        return Builder.load_string(KV)

    def on_start(self):
        self.load_families()

    # --- Database Functions ---
    def db_init(self):
        self.conn = sqlite3.connect("gurudwara_v2.db")
        self.cursor = self.conn.cursor()
        
        # Table 1: Families
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                land_area REAL,
                balance_due REAL
            )
        """)
        
        # Table 2: History (Transactions)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER,
                date_time TEXT,
                description TEXT,
                amount REAL,
                type TEXT 
            )
        """)
        # type can be 'DEBIT' (Fee added) or 'CREDIT' (Payment made)
        self.conn.commit()

    # --- SCREEN 1: Home Logic ---
    def load_families(self, search_text=""):
        self.root.ids.container.clear_widgets()
        
        query = "SELECT * FROM families"
        params = ()
        if search_text:
            query += " WHERE name LIKE ?"
            params = (f"%{search_text}%",)
            
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()

        for row in rows:
            f_id, name, land, due = row
            item = FamilyItem(
                text=f"{name}",
                secondary_text=f"Land: {land} Acres",
                tertiary_text=f"Due: ₹{due:.2f}",
                family_id=str(f_id)
            )
            icon = IconLeftWidget(icon="home-outline")
            item.add_widget(icon)
            # When clicked, go to detail screen
            item.bind(on_release=lambda x: self.open_detail_screen(x.family_id))
            self.root.ids.container.add_widget(item)

    def filter_list(self, text):
        self.load_families(text)

    # --- SCREEN 2: Detail Logic ---
    def open_detail_screen(self, family_id):
        self.current_family_id = family_id
        # Switch screen
        self.root.ids.screen_manager.current = "detail_screen"
        # Add a back button to the top bar
        self.root.ids.top_bar.left_action_items = [["arrow-left", lambda x: self.go_back()]]
        self.root.ids.top_bar.title = "Family Details"

    def go_back(self):
        self.root.ids.screen_manager.current = "home_screen"
        self.root.ids.top_bar.left_action_items = [] # Remove back button
        self.root.ids.top_bar.title = "Gurudwara Donation Tracker"
        self.load_families() # Refresh list to show updated balances

    def load_history(self):
        if not self.current_family_id:
            return
            
        # 1. Load Family Info
        self.cursor.execute("SELECT name, land_area, balance_due FROM families WHERE id = ?", (self.current_family_id,))
        fam = self.cursor.fetchone()
        if fam:
            self.root.ids.detail_name.text = str(fam[0])
            self.root.ids.detail_land.text = f"Land Owned: {fam[1]} Acres"
            self.root.ids.detail_balance.text = f"Current Due: ₹{fam[2]:.2f}"

        # 2. Load History
        self.root.ids.history_container.clear_widgets()
        self.cursor.execute("SELECT date_time, description, amount, type FROM transactions WHERE family_id = ? ORDER BY id DESC", (self.current_family_id,))
        rows = self.cursor.fetchall()
        
        for row in rows:
            dt, desc, amt, trans_type = row
            color = "green" if trans_type == "CREDIT" else "red"
            sign = "-" if trans_type == "CREDIT" else "+"
            
            item = TransactionItem(
                text=f"{desc} ({sign}₹{amt})",
                secondary_text=f"{dt}",
                theme_text_color="Custom",
                text_color=color
            )
            self.root.ids.history_container.add_widget(item)

    # --- Feature: Add New Family (Updated) ---
    def show_add_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="180dp")
        self.name_field = MDTextField(hint_text="Family Name")
        self.land_field = MDTextField(hint_text="Land Area (Acres)", input_filter="float")
        self.initial_due_field = MDTextField(hint_text="Previous Due Amount (if any)", input_filter="float", text="0")
        
        content.add_widget(self.name_field)
        content.add_widget(self.land_field)
        content.add_widget(self.initial_due_field)

        self.dialog = MDDialog(
            title="Add New Family",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.close_dialog),
                MDRaisedButton(text="SAVE", on_release=self.add_family_to_db),
            ],
        )
        self.dialog.open()

    def add_family_to_db(self, obj):
        name = self.name_field.text
        land = self.land_field.text
        initial_due = self.initial_due_field.text
        
        if name and land:
            # 1. Create Family
            self.cursor.execute("INSERT INTO families (name, land_area, balance_due) VALUES (?, ?, ?)", 
                                (name, float(land), float(initial_due)))
            new_id = self.cursor.lastrowid
            
            # 2. Add Initial Transaction Record if due > 0
            if float(initial_due) > 0:
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.cursor.execute("INSERT INTO transactions (family_id, date_time, description, amount, type) VALUES (?, ?, ?, ?, ?)",
                                    (new_id, dt, "Initial Balance", float(initial_due), "DEBIT"))
            
            self.conn.commit()
            self.load_families()
            self.close_dialog()

    # --- Feature: New Period Collection (Updated to log history) ---
    def show_period_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="60dp")
        self.rate_field = MDTextField(hint_text="Rate per Acre (e.g. 500)", input_filter="float")
        content.add_widget(self.rate_field)

        self.dialog = MDDialog(
            title="Start New Collection",
            text="Add periodic fee to ALL families?",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.close_dialog),
                MDRaisedButton(text="APPLY", text_color="red", on_release=self.apply_period_update),
            ],
        )
        self.dialog.open()

    def apply_period_update(self, obj):
        rate_text = self.rate_field.text
        if rate_text:
            rate = float(rate_text)
            dt = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # We need to loop through everyone to record the history correctly for each person
            self.cursor.execute("SELECT id, land_area FROM families")
            all_families = self.cursor.fetchall()
            
            for fam in all_families:
                f_id, land = fam
                fee = land * rate
                if fee > 0:
                    # Update Balance
                    self.cursor.execute("UPDATE families SET balance_due = balance_due + ? WHERE id = ?", (fee, f_id))
                    # Add History Record
                    self.cursor.execute("INSERT INTO transactions (family_id, date_time, description, amount, type) VALUES (?, ?, ?, ?, ?)",
                                        (f_id, dt, f"Periodic Fee (@{rate}/acre)", fee, "DEBIT"))
            
            self.conn.commit()
            self.load_families() # Refresh current view
            self.close_dialog()

    # --- Feature: Make Payment (Updated logic) ---
    def show_payment_dialog(self):
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="60dp")
        self.pay_field = MDTextField(hint_text="Amount Received", input_filter="float")
        content.add_widget(self.pay_field)

        self.dialog = MDDialog(
            title="Record Payment",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.close_dialog),
                MDRaisedButton(text="PAY", on_release=self.process_payment),
            ],
        )
        self.dialog.open()

    def process_payment(self, obj):
        amount_text = self.pay_field.text
        if amount_text and self.current_family_id:
            amount = float(amount_text)
            dt = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 1. Update Balance
            self.cursor.execute("UPDATE families SET balance_due = balance_due - ? WHERE id = ?", (amount, self.current_family_id))
            
            # 2. Add History Record
            self.cursor.execute("INSERT INTO transactions (family_id, date_time, description, amount, type) VALUES (?, ?, ?, ?, ?)",
                                (self.current_family_id, dt, "Payment Received", amount, "CREDIT"))
            
            self.conn.commit()
            self.load_history() # Refresh the details page immediately
            self.close_dialog()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()

if __name__ == "__main__":
    DonationApp().run()