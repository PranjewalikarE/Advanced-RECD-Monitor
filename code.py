from tkinter import ttk
import tkinter as tk
from Db_handler import init_db, load_machines
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox
from New_Machine_Button import open_add_machine_window
from data_decoder import decode_hex_data
from Report_Button import open_report_window
from datetime import datetime
from Db_handler import insert_fault_log


class MachineDataViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced RECD Monitor")
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.genset_on_count = 0
        self.genset_off_count = 0
        self.machines = load_machines()
        self.lock = threading.Lock()
        self.fault_data = {}
        self.decoded_data_store = {}
        self.open_detail_windows = {}

        # Updated fault_code_mapping to include 'No Error'
        self.fault_code_mapping = {
            0: 'No Error',
            1: 'Internal or wiring short detected',
            2: 'Open HV side connection',
            3: 'Exhaust bypass or Thermostat switch broken (Permanently Closed)',
            4: 'Genset ON signal wire is disconnected',
            5: 'Drive chain dropped or Open motor electrical circuit',
            6: 'Jammed scraper mechanism or motor wiring short',
            7: 'Scraping cycle pending (Genset running)',
            8: 'Reminder for soot extraction from bins',
            9: 'The scraper motor is not at parking position',
            11: 'Inducement Active',
            12: 'Emergency Stop Engaged',
            13: 'Shaker Motor - no load/disconnected',
            14: 'Shaker Mechanism jam or motor wiring short'
        }

        self.setup_ui()
        self.fetch_all_machine_data()
        self.schedule_refresh()

    def setup_ui(self):
        screen_width = self.root.winfo_screenwidth()
        cm_to_px = lambda cm: int((96 / 2.54) * cm)
        spacing_0_5cm = cm_to_px(0.5)

        top_frame = tk.Frame(self.root, bg="#f5f5f5")
        top_frame.pack(pady=10, padx=10, fill="x")

        tk.Button(
            top_frame,
            text="Add New Machine",
            command=lambda: open_add_machine_window(self),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        ).pack(side="left", padx=5)

        self.category_box = tk.LabelFrame(
            self.root,
            text="Error Categories",
            font=("Arial", 12, "bold"),
            fg="#333",
            bg="white",
            padx=10,
            pady=10,
            bd=3,
            relief="ridge",
        )
        self.category_box.pack(side="left", padx=spacing_0_5cm, pady=10, anchor="nw")

        category_frame = tk.Frame(self.category_box, bg="white")
        category_frame.pack()

        self.category_boxes = {}
        rows, cols = 5, 3
        row, col = 0, 0

        # Sort keys to ensure '0' (No Error) comes first if desired, or just by numeric order
        for code in sorted(self.fault_code_mapping.keys()):
            box_frame = tk.Frame(category_frame, bg="white", bd=2, relief="groove")
            box_frame.grid(row=row, column=col, padx=5, pady=5)
            box_frame.configure(width=250, height=150)

            tk.Label(
                box_frame,
                text=f"Fault Code {code}",
                font=("Arial", 10, "bold"),
                bg="#F0F0F0"
            ).pack(fill="x")

            list_frame = tk.Frame(box_frame, bg="white")
            list_frame.pack(fill="both", expand=True)

            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side="right", fill="y")

            listbox = tk.Listbox(
                list_frame,
                yscrollcommand=scrollbar.set,
                bg="white",
                font=("Arial", 9),
                height=5,
            )
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)

            self.category_boxes[code] = listbox

            listbox.bind("<<ListboxSelect>>", self.on_category_machine_click)

            col += 1
            if col >= cols:
                col = 0
                row += 1

        # -------------------- Center Panel - Error Viewer --------------------
        center_frame = tk.Frame(self.root, bg="white")
        center_frame.pack(
            side="left",
            padx=(spacing_0_5cm + cm_to_px(0.5), spacing_0_5cm),
            pady=10,
            expand=True,
        )

        self.fault_box = tk.LabelFrame(
            center_frame,
            text="Error Viewer",
            font=("Arial", 12, "bold"),
            fg="#333",
            bg="white",
            padx=10,
            pady=10,
            bd=2,
            relief="groove",
        )
        self.fault_box.pack(pady=20)

        search_frame = tk.Frame(self.fault_box, bg="white")
        search_frame.pack(pady=5, anchor="e")

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_frame, textvariable=self.search_var, font=("Arial", 10), width=30
        )
        search_entry.pack(side="left", padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.search_and_open_machine())

        search_button = tk.Button(
            search_frame,
            text="Search",
            font=("Arial", 9, "bold"),
            bg="#2196F3",
            fg="white",
            command=self.search_and_open_machine,
        )
        search_button.pack(side="left")

        self.error_machine_listbox = tk.Listbox(
        self.fault_box, width=30, height=40, font=("Arial", 10)
        )
        self.error_machine_listbox.pack()
        self.error_machine_listbox.bind("<<ListboxSelect>>", self.show_fault_details)

        # -------------------- Right Panel - RECD Status --------------------
        self.gauge_box = tk.LabelFrame(
            self.root,
            text="RECD Status",
            font=("Arial", 12, "bold"),
            fg="#333",
            bg="white",
            padx=10,
            pady=10,
            bd=3,
            relief="ridge",
        )
        self.gauge_box.pack(
            side="right",
            padx=spacing_0_5cm,
            pady=10,
            anchor="ne"
        )

        self.gauge_frame = tk.Frame(self.gauge_box, bg="white")
        self.gauge_frame.pack()

        tk.Label(
            self.gauge_frame,
            text="ON",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#4CAF50",
        ).pack(pady=(5, 2))

        self.on_gauge_canvas = tk.Canvas(
            self.gauge_frame, width=200, height=212, bg="white", highlightthickness=0
        )
        self.on_gauge_canvas.pack()

        tk.Label(
            self.gauge_frame,
            text="OFF",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#F44336",
        ).pack(pady=(5, 2))

        self.off_gauge_canvas = tk.Canvas(
            self.gauge_frame, width=212, height=212, bg="white", highlightthickness=0
        )
        self.off_gauge_canvas.pack()

        self.total_label = tk.Label(
            self.gauge_frame,
            text="Total Devices: 0",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#333",
        )
        self.total_label.pack(pady=(5, 0))

        self.online_label = tk.Label(
            self.gauge_frame,
            text="Online: 0",
            font=("Arial", 10),
            bg="white",
            fg="#333",
        )
        self.online_label.pack()

        self.offline_label = tk.Label(
            self.gauge_frame,
            text="Offline: 0",
            font=("Arial", 10),
            bg="white",
            fg="#333",
        )
        self.offline_label.pack(pady=(0, 10))

    def search_and_open_machine(self):
        query = self.search_var.get().strip()
        if not query:
            return
        for idx in range(self.error_machine_listbox.size()):
            item_text = self.error_machine_listbox.get(idx)
            if item_text.lower() == query.lower():
                self.error_machine_listbox.selection_clear(0, tk.END)
                self.error_machine_listbox.selection_set(idx)
                self.error_machine_listbox.event_generate("<<ListboxSelect>>")
                return
        messagebox.showwarning(
            "Not Found", f"No machine named '{query}' found in the Error Viewer."
        )

    def update_error_category_box(self):
        # सर्व listbox clear करा
        for lb in self.category_boxes.values():
            lb.delete(0, tk.END)

        # प्रत्येक fault code साठी unique मशीन नावे track करा
        shown = {k: set() for k in self.fault_code_mapping.keys()}

        for full_vm, decoded in self.decoded_data_store.items():
            if full_vm not in self.fault_data or decoded.get("No Data"):
                continue

            fault_code = self.fault_data[full_vm]
            base_machine_name = full_vm.split(' - ')[0]

            if fault_code in self.fault_code_mapping:
                if base_machine_name not in shown[fault_code]:
                    self.category_boxes[fault_code].insert(tk.END, base_machine_name)
                    shown[fault_code].add(base_machine_name)

        # प्रत्येक ListBox मध्ये Total Count जोडा
        for code, lb in self.category_boxes.items():
            lb.insert(tk.END, "-" * 30)
            count = len(shown[code])
            total_text = f"Total: {count} machine(s)"
            lb.insert(tk.END, total_text)

        for code, lb in self.category_boxes.items():
            lb.insert(tk.END, "-" * 30)
            count = len(shown[code])
            total_text = f"Total: {count} machine(s)"
            lb.insert(tk.END, total_text)

            # 'Total' टेक्स्ट highlight करा
            last_idx = lb.size() - 1
            if count > 0:
                lb.itemconfig(last_idx, {'fg': 'blue', 'font': ("Arial", 9, "bold")})
            else:
                lb.itemconfig(last_idx, {'fg': 'gray', 'font': ("Arial", 9, "bold")})

    def on_category_machine_click(self, event):
        listbox = event.widget
        selection = listbox.curselection()
        if not selection:
            return

        selected_machine = listbox.get(selection[0])

        # Ignore if line is separator or total count
        if selected_machine.startswith("-") or selected_machine.startswith("Total"):
            return

        # Open new detail window with all M1 to M8
        if selected_machine in self.open_detail_windows:
            win = self.open_detail_windows[selected_machine]
            win.lift()
            win.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title(f"Details for {selected_machine}")
        win.geometry("800x600")
        self.open_detail_windows[selected_machine] = win
        win.protocol("WM_DELETE_WINDOW", lambda: (self.open_detail_windows.pop(selected_machine, None), win.destroy()))
        self.rebuild_fault_detail_window(selected_machine, win)

        # Left Scrollable Frame
        container = tk.Frame(win, bg="white")
        container.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(container, bg="white")
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Display all M1 to M8 data for selected VM
        for vm in range(1, 9):
            full_vm_name = f"{selected_machine} - M{vm}"
            decoded = self.decoded_data_store.get(full_vm_name)
            fault_code = self.fault_data.get(full_vm_name, None)

            section = tk.LabelFrame(
                scrollable_frame,
                text=full_vm_name,
                font=("Arial", 10, "bold"),
                padx=5,
                pady=5,
                bg="white",
                fg="black",
            )
            section.pack(fill="x", expand=True, padx=10, pady=5)

            if not decoded or decoded.get("No Data"):
                tk.Label(
                    section,
                    text="No data",
                    font=("Arial", 9, "italic"),
                    bg="white",
                    fg="gray",
                ).pack(anchor="w")
                continue

            for key, val in decoded.items():
                if key in ("No Data", "Raw Value"):
                    continue
                fg_color = "red" if key == "Fault Code" else "black"
                display_text = f"{key}: {val}"
                tk.Label(
                    section,
                    text=display_text,
                    font=("Arial", 9),
                    bg="white",
                    fg=fg_color,
                    anchor="w",
                ).pack(fill="x")

        # Report section (right)
        right_frame = tk.Frame(win, bg="white")
        right_frame.pack(side="right", fill="y", padx=20, pady=20)

        tk.Label(
            right_frame,
            text="Select the Machine",
            font=("Arial", 11, "bold"),
            bg="white",
            anchor="w",
        ).pack(pady=(0, 10))

        selected_vm = tk.StringVar()
        vm_options = [f"{selected_machine} M{vm}" for vm in range(1, 9)]
        vm_dropdown = tk.OptionMenu(right_frame, selected_vm, *vm_options)
        vm_dropdown.config(font=("Arial", 10), bg="#e0e0e0")
        vm_dropdown.pack(pady=(0, 20))

        def on_generate_report():
            machine_name = selected_vm.get().strip()
            if machine_name:
                open_report_window(machine_name)

        tk.Button(
            right_frame,
            text="Generate Report",
            font=("Arial", 10, "bold"),
            bg="#2196F3",
            fg="white",
            command=on_generate_report,
        ).pack()


    def refresh_fault_viewer(self):
        self.error_machine_listbox.delete(0, tk.END)
        # Only show machines that have an actual fault (fault_code != 0)
        machine_names_with_faults = set(full.split(" - ")[0] for full, code in self.fault_data.items() if code != 0)
        for name in sorted(machine_names_with_faults):
            self.error_machine_listbox.insert(tk.END, name)

    # ------------------------------------------------------------------
    #           Detail Window Management
    # ------------------------------------------------------------------

    def show_fault_details(self, event):
        sel = self.error_machine_listbox.curselection()
        if not sel:
            return
        machine = self.error_machine_listbox.get(sel[0])
        if machine in self.open_detail_windows:
            win = self.open_detail_windows[machine]
            win.lift()
            win.focus_force()
            return
        win = tk.Toplevel(self.root)
        self.open_detail_windows[machine] = win
        win.protocol(
            "WM_DELETE_WINDOW", lambda: (self.open_detail_windows.pop(machine, None), win.destroy())
        )
        self.rebuild_fault_detail_window(machine, win)

    def rebuild_fault_detail_window(self, selected_machine, detail_win):
        for widget in detail_win.winfo_children():
            widget.destroy()
        detail_win.title(f"Details for {selected_machine}")
        detail_win.geometry("800x600")

        container = tk.Frame(detail_win, bg="white")
        container.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(container, bg="white")
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for vm in range(1, 9):
            full_name = f"{selected_machine} - M{vm}"
            decoded = self.decoded_data_store.get(full_name)
            fault_code = self.fault_data.get(full_name, None)

            section = tk.LabelFrame(
                scrollable_frame,
                text=full_name,
                font=("Arial", 10, "bold"),
                padx=5,
                pady=5,
                bg="white",
                fg="black",
            )
            section.pack(fill="x", expand=True, padx=10, pady=5)

            if not decoded or decoded.get("No Data"):
                tk.Label(
                    section,
                    text="No data",
                    font=("Arial", 9, "italic"),
                    bg="white",
                    fg="gray",
                ).pack(anchor="w")
                continue

            for key, val in decoded.items():
                if key in ("No Data", "Raw Value"):
                    continue
                fg_color = "red" if key == "Fault Code" else "black"
                display_text = f"{key}: {val}"
                tk.Label(
                    section,
                    text=display_text,
                    font=("Arial", 9),
                    bg="white",
                    fg=fg_color,
                    anchor="w",
                ).pack(fill="x")

        # Report section (right side)
        right_frame = tk.Frame(detail_win, bg="white")
        right_frame.pack(side="right", fill="y", padx=20, pady=20)
        tk.Label(
            right_frame,
            text="Select the Machine",
            font=("Arial", 11, "bold"),
            bg="white",
            anchor="w",
        ).pack(pady=(0, 10))
        selected_vm = tk.StringVar()
        vm_options = [f"{selected_machine} M{vm}" for vm in range(1, 9)]
        vm_dropdown = tk.OptionMenu(right_frame, selected_vm, *vm_options)
        vm_dropdown.config(font=("Arial", 10), bg="#e0e0e0")
        vm_dropdown.pack(pady=(0, 20))

        def on_generate_report():
            machine_name = selected_vm.get().strip()
            if machine_name:
                open_report_window(machine_name)

        tk.Button(
            right_frame,
            text="Generate Report",
            font=("Arial", 10, "bold"),
            bg="#2196F3",
            fg="white",
            command=on_generate_report,
        ).pack()


    # ------------------------------------------------------------------
    #           Data Fetch & Decode
    # ------------------------------------------------------------------

    def clear_display(self):
        self.fault_data.clear()
        self.decoded_data_store.clear()
        self.genset_on_count = 0
        self.genset_off_count = 0

    def fetch_all_machine_data(self):
        self.clear_display()
        self.completed_count = 0
        self.total_machines_to_process = len(self.machines)
        for name, info in self.machines.items():
            self.executor.submit(self.process_machine, name, info)

    def process_machine(self, name, info):
        url = (
            f"https://api.thingspeak.com/channels/{info['channel_id']}/feeds.json?api_key="
            f"{info['api_key']}&results=1"
        )
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            feeds = response.json().get("feeds", [])

            # ✅ Even if no feeds, still show machine in GUI
            if not feeds:
                print(f"[WARN] No data for machine: {name}")
                with self.lock:
                    for i in range(1, 9):
                        virtual_machine_name = f"{name} - M{i}"
                        self.decoded_data_store[virtual_machine_name] = {"No Data": True}
                        self.fault_data[virtual_machine_name] = 0
                        self.genset_off_count += 1
                return

            feed = feeds[0]
            for i in range(1, 9):
                virtual_machine_name = f"{name} - M{i}"
                raw_value = feed.get(f"field{i}", "") or ""
                raw_str = str(raw_value).strip()

                try:
                    if raw_str:
                        decimal_int = int(raw_str)
                        no_data = False
                    else:
                        raise ValueError
                except Exception:
                    try:
                        decimal_int = int(float(raw_str)) if raw_str else 0
                        no_data = False if raw_str else True
                    except Exception:
                        decimal_int = 0
                        no_data = True

                hex_str = hex(decimal_int)[2:].zfill(16).upper()

                # ✅ Save hex to DB
                try:
                    insert_fault_log(name, f"M{i}", hex_str)
                    print(f"[LOG] Inserted {name} - M{i} → {hex_str}")
                except Exception as e:
                    print(f"[ERROR] Insert failed for {name} - M{i}: {e}")

                # Decode
                try:
                    decoded = decode_hex_data(hex_str)
                except Exception as e:
                    print(f"[ERROR] Decode failed for {name} - M{i}: {e}")
                    decoded = {}

                decoded["Raw Value"] = raw_str if raw_str else "No Data"
                decoded["No Data"] = no_data
                signal = decoded.get("Genset Signal", "").upper()

                with self.lock:
                    self.decoded_data_store[virtual_machine_name] = decoded
                    if signal == "ON":
                        self.genset_on_count += 1
                    else:
                        self.genset_off_count += 1

                    code_val = decoded.get("Fault Code", 0)
                    try:
                        fault_code = int(code_val, 2) if str(code_val).startswith("0b") else int(code_val)
                    except Exception:
                        fault_code = 0
                    self.fault_data[virtual_machine_name] = fault_code

        except Exception as e:
            print(f"[ERROR] API fetch failed for {name}: {e}")
            with self.lock:
                for i in range(1, 9):
                    virtual_machine_name = f"{name} - M{i}"
                    self.decoded_data_store[virtual_machine_name] = {"No Data": True}
                    self.fault_data[virtual_machine_name] = 0
                    self.genset_off_count += 1
        finally:
            with self.lock:
                self.completed_count += 1
                if self.completed_count >= self.total_machines_to_process:
                    total = len(self.machines) * 8
                    self.root.after(0, self.update_gauges)
                    self.root.after(0, self.update_status_labels, total, self.genset_on_count + self.genset_off_count)
                    self.root.after(0, self.refresh_fault_viewer)
                    self.root.after(0, self.update_error_category_box)
                    self.root.after(0, self.refresh_open_detail_windows)

    # ------------------------------------------------------------------
    #           Gauges & Status Labels
    # ------------------------------------------------------------------

    def draw_on_gauge(self, value, total):
        self.on_gauge_canvas.delete("all")
        cx, cy, r = 106, 106, 81
        sweep = 180 * (value / total) if total else 0
        self.on_gauge_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill="#e0e0e0", outline=""
        )
        self.on_gauge_canvas.create_arc(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            start=90,
            extent=sweep,
            fill="#4CAF50",
            outline="",
        )
        self.on_gauge_canvas.create_text(
            cx, cy - 10, text=str(value), font=("Arial", 20, "bold"), fill="white"
        )
        pct = (value / total) * 100 if total else 0
        self.on_gauge_canvas.create_text(
            cx, cy + 15, text=f"{pct:.1f}%", font=("Arial", 12), fill="white"
        )

    def draw_off_gauge(self, value, total):
        self.off_gauge_canvas.delete("all")
        cx, cy, r = 106, 106, 81
        sweep = 180 * (value / total) if total else 0
        self.off_gauge_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill="#e0e0e0", outline=""
        )
        self.off_gauge_canvas.create_arc(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            start=90,
            extent=sweep,
            fill="#F44336",
            outline="",
        )
        self.off_gauge_canvas.create_text(
            cx, cy - 10, text=str(value), font=("Arial", 20, "bold"), fill="white"
        )
        pct = (value / total) * 100 if total else 0
        self.off_gauge_canvas.create_text(
            cx, cy + 15, text=f"{pct:.1f}%", font=("Arial", 12), fill="white"
        )

    def update_gauges(self):
        total = self.genset_on_count + self.genset_off_count
        if total == 0:
            total = 1 
        self.draw_on_gauge(self.genset_on_count, total)
        self.draw_off_gauge(self.genset_off_count, total)

    def update_status_labels(self, total_virtual_machines, online_count):
        self.total_label.config(text=f"Total Devices: {total_virtual_machines}")
        self.online_label.config(text=f"Online: {online_count}")
        self.offline_label.config(text=f"Offline: {total_virtual_machines - online_count}")

    # ------------------------------------------------------------------
    #           Periodic Refresh Scheduling
    # ------------------------------------------------------------------

    def refresh_open_detail_windows(self):
        for machine_name, win in list(self.open_detail_windows.items()):
            if win.winfo_exists():
                self.rebuild_fault_detail_window(machine_name, win)
            else:
                self.open_detail_windows.pop(machine_name, None)

    def schedule_refresh(self):
        self.root.after(180_000, self.refresh_data)

    def refresh_data(self):
        self.machines = load_machines()
        self.fetch_all_machine_data()
        self.schedule_refresh()


if __name__ == "__main__":
    from admin_login import AdminLoginWindow, CreateAdminWindow
    from Db_handler import init_db, has_any_admin

    init_db()
    root = tk.Tk()
    root.withdraw()  # hide main window until login

    def open_main_app():
        root.deiconify()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.geometry(f"{screen_width}x{screen_height}")
        app = MachineDataViewerApp(root)
        root.mainloop()

    def show_login():
        AdminLoginWindow(root, on_success=open_main_app)

    # जर अजून admin user नाही → CreateAdminWindow दाखव
    if not has_any_admin():
        CreateAdminWindow(root, on_created=show_login)
    else:
        AdminLoginWindow(root, on_success=open_main_app)

    root.mainloop()