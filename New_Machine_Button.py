import tkinter as tk
from tkinter import messagebox, filedialog
from tkcalendar import DateEntry
import openpyxl
import sqlite3
from Db_handler import add_machine, update_machine_full, insert_from_excel

def open_add_machine_window(app):
    window = tk.Toplevel(app.root)
    window.title("Add New Machine")

    tk.Label(window, text="Machine Name").grid(row=0, column=0)
    tk.Label(window, text="Channel ID").grid(row=1, column=0)
    tk.Label(window, text="API Key").grid(row=2, column=0)

    name_entry = tk.Entry(window)
    channel_entry = tk.Entry(window)
    key_entry = tk.Entry(window)

    name_entry.grid(row=0, column=1)
    channel_entry.grid(row=1, column=1)
    key_entry.grid(row=2, column=1)

    # Controller Header
    tk.Label(window, text="Controller").grid(row=4, column=0)
    tk.Label(window, text="Controller No.").grid(row=4, column=1)
    tk.Label(window, text="Customer Name").grid(row=4, column=2)
    tk.Label(window, text="Mfg Date").grid(row=4, column=3)
    tk.Label(window, text="Installation Date").grid(row=4, column=4)

    controller_entries = []

    for i in range(8):
        tk.Label(window, text=f"M{i+1}").grid(row=5+i, column=0)

        ctrl_entry = tk.Entry(window)
        cust_entry = tk.Entry(window)
        mfg_entry = DateEntry(window, width=12, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
        inst_entry = DateEntry(window, width=12, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')

        ctrl_entry.grid(row=5+i, column=1)
        cust_entry.grid(row=5+i, column=2)
        mfg_entry.grid(row=5+i, column=3)
        inst_entry.grid(row=5+i, column=4)

        controller_entries.append({
            "name": f"M{i+1}",
            "controller_no": ctrl_entry,
            "customer_name": cust_entry,
            "mfg_date": mfg_entry,
            "inst_date": inst_entry
        })

    def save():
        name = name_entry.get().strip()
        channel = channel_entry.get().strip()
        key = key_entry.get().strip()

        if not name or not channel or not key:
            messagebox.showerror("Input Error", "Machine Name, Channel ID and API Key are required.")
            return

        controller_data = []
        for item in controller_entries:
            ctrl_no = item["controller_no"].get().strip()
            cust_name = item["customer_name"].get().strip()
            mfg_date = item["mfg_date"].get()
            inst_date = item["inst_date"].get()

            if ctrl_no or cust_name:
                controller_data.append({
                    "controller": item["name"],
                    "controller_no": ctrl_no,
                    "customer_name": cust_name,
                    "mfg_date": mfg_date,
                    "inst_date": inst_date
                })

        try:
            add_machine(name, channel, key, controller_data)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: machines.name" in str(e):
                messagebox.showwarning("Duplicate Machine", "Machine already stored!")
            else:
                messagebox.showerror("Database Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add machine: {e}")
            return

        messagebox.showinfo("Success", "Machine added with full details.")
        window.destroy()
        app.refresh_data()

    tk.Button(window, text="Save", command=save).grid(row=14, column=0, columnspan=5, pady=10)

    def attach_excel():
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not file_path:
            return

        try:
            insert_from_excel(file_path)
            messagebox.showinfo("Success", "Excel data imported successfully.")
            app.refresh_data()
        except Exception as e:
            messagebox.showerror("Error", f"Excel import failed: {e}")

    tk.Button(window, text="Save", command=save).grid(row=14, column=0, columnspan=5, pady=10)
    tk.Button(window, text="📎 Attach Excel File", command=attach_excel).grid(row=15, column=0, columnspan=5, pady=10)
    tk.Button(window, text="Change Machine Details", command=lambda: open_change_window(app)).grid(row=16, column=0, columnspan=5, pady=10)


def open_change_window(app):
    change_window = tk.Toplevel(app.root)
    change_window.title("Change Machine Details")

    tk.Label(change_window, text="Old Machine Name").grid(row=0, column=0)
    tk.Label(change_window, text="New Machine Name").grid(row=0, column=1)

    tk.Label(change_window, text="Old Channel ID").grid(row=1, column=0)
    tk.Label(change_window, text="New Channel ID").grid(row=1, column=1)

    tk.Label(change_window, text="Old API Key").grid(row=2, column=0)
    tk.Label(change_window, text="New API Key").grid(row=2, column=1)

    old_name = tk.Entry(change_window)
    new_name = tk.Entry(change_window)
    old_channel = tk.Entry(change_window)
    new_channel = tk.Entry(change_window)
    old_key = tk.Entry(change_window)
    new_key = tk.Entry(change_window)

    old_name.grid(row=3, column=0)
    new_name.grid(row=3, column=1)
    old_channel.grid(row=4, column=0)
    new_channel.grid(row=4, column=1)
    old_key.grid(row=5, column=0)
    new_key.grid(row=5, column=1)

    # Controller No. Update Header
    tk.Label(change_window, text="Controller").grid(row=6, column=0)
    tk.Label(change_window, text="Old Controller No.").grid(row=6, column=1)
    tk.Label(change_window, text="New Controller No.").grid(row=6, column=2)

    controller_entries = []

    for i in range(8):
        tk.Label(change_window, text=f"M{i+1}").grid(row=7+i, column=0)

        old_ctrl = tk.Entry(change_window)
        new_ctrl = tk.Entry(change_window)

        old_ctrl.grid(row=7+i, column=1)
        new_ctrl.grid(row=7+i, column=2)

        controller_entries.append({
            "controller": f"M{i+1}",
            "old_no": old_ctrl,
            "new_no": new_ctrl
        })

    def update():
        old_n = old_name.get().strip()
        new_n = new_name.get().strip()
        old_c = old_channel.get().strip()
        new_c = new_channel.get().strip()
        old_k = old_key.get().strip()
        new_k = new_key.get().strip()

        if not all([old_n, new_n, old_c, new_c, old_k, new_k]):
            messagebox.showerror("Input Error", "All main fields are required.")
            return

        controller_updates = []
        for item in controller_entries:
            old_no = item["old_no"].get().strip()
            new_no = item["new_no"].get().strip()
            if old_no or new_no:
                controller_updates.append({
                    "controller": item["controller"],
                    "old_no": old_no,
                    "new_no": new_no
                })

        updated = update_machine_full(old_n, new_n, old_c, new_c, old_k, new_k, controller_updates)

        if updated:
            messagebox.showinfo("Success", "Machine details updated.")
            change_window.destroy()
            app.refresh_data()
        else:
            messagebox.showerror("Error", "Old machine details not found or incorrect.")
