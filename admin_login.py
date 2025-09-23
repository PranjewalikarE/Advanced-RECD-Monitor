import tkinter as tk
from tkinter import messagebox, simpledialog
from Db_handler import get_admin, reset_admin, list_admins, create_admin

# ----------- First Admin Creation Window -----------
class CreateAdminWindow(tk.Toplevel):
    def __init__(self, master, on_created):
        super().__init__(master)
        self.title("Create Admin")
        self.geometry("300x220")
        self.resizable(False, False)
        self.on_created = on_created

        tk.Label(self, text="Create First Admin", font=("Arial", 14, "bold")).pack(pady=10)

        tk.Label(self, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(self)
        self.username_entry.pack(pady=5)

        tk.Label(self, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(
            self, text="Create Admin", bg="#4CAF50", fg="white",
            command=self.create_admin
        ).pack(pady=10)

    def create_admin(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Both fields are required.")
            return

        try:
            create_admin(username, password)
            messagebox.showinfo("Success", f"Admin '{username}' created successfully!")
            self.destroy()
            self.on_created()  # After admin created, show login window
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create admin: {e}")


# ----------- Admin Login Window -----------
class AdminLoginWindow(tk.Toplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.title("Admin Login")
        self.geometry("300x220")
        self.resizable(False, False)
        self.on_success = on_success

        tk.Label(self, text="Admin Login", font=("Arial", 14, "bold")).pack(pady=10)

        tk.Label(self, text="Username:").pack(pady=5)
        self.username_entry = tk.Entry(self)
        self.username_entry.pack(pady=5)

        tk.Label(self, text="Password:").pack(pady=5)
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        tk.Button(
            self, text="Login", bg="#4CAF50", fg="white",
            command=self.check_credentials
        ).pack(pady=10)

        tk.Button(
            self, text="Forgot Password?", fg="blue", relief="flat",
            command=self.reset_password
        ).pack()

    def check_credentials(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if get_admin(username, password):
            messagebox.showinfo("Success", "Admin login successful!")
            self.destroy()
            self.on_success()
        else:
            messagebox.showerror("Error", "Invalid admin credentials")

    def reset_password(self):
        admins = list_admins()
        if not admins:
            messagebox.showerror("Error", "No admin users found.")
            return

        username = simpledialog.askstring("Reset Password", f"Enter admin username ({', '.join(admins)}):")
        if not username:
            return

        new_pass = simpledialog.askstring("Reset Password", "Enter new password:", show="*")
        if not new_pass:
            return

        if reset_admin(username, new_pass):
            messagebox.showinfo("Success", f"Password reset for {username}")
        else:
            messagebox.showerror("Error", f"Admin {username} not found!")
