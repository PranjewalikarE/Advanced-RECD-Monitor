import tkinter as tk

# Fault code to error title from Excel
fault_code_mapping = {
    0: 'Secondary Voltage Below Desired Level',
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

# Store faults under their respective error titles
main_error_data = {error: [] for error in fault_code_mapping.values()}

def update_fault_data(machine_name, field_no, fault_code):
    title = fault_code_mapping.get(fault_code)
    if title:
        main_error_data[title].append({
            "machine": machine_name,
            "field_no": field_no,
            "code": fault_code
        })

def create_fault_code_viewer(parent_frame, detail_frame):
    main_box = tk.LabelFrame(parent_frame, text="Fault Code Viewer", bg="#f5f5f5",
                             font=("Arial", 12, "bold"), padx=10, pady=10)
    main_box.pack(fill="both", expand=False, pady=(10, 0))

    box_frame = tk.Frame(main_box, bg="#f5f5f5")
    box_frame.pack()

    row, col, max_cols = 2, 0, 2

    def on_category_click(category):
        show_fault_detail_frame(detail_frame, category)

    for title in fault_code_mapping.values():
        box = tk.Frame(box_frame, bg="white", bd=1, relief="solid", width=200, height=100)
        box.grid(row=row, column=col, padx=5, pady=5)
        box.grid_propagate(False)

        btn = tk.Button(box, text=title, font=("Arial", 10, "bold"),
                        bg="white", relief="flat", wraplength=180,
                        command=lambda t=title: on_category_click(t))
        btn.pack(anchor="w", padx=5, pady=(5, 0))

        tk.Label(box, text="Status: Error Detected", font=("Arial", 9), bg="white", fg="#d32f2f").pack(anchor="w", padx=5)

        col += 1
        if col >= max_cols:
            col = 0
            row += 1

def show_fault_detail_frame(detail_frame, category):
    for widget in detail_frame.winfo_children():
        widget.destroy()

    tk.Label(detail_frame, text=category, font=("Arial", 14, "bold"), bg="white").pack(pady=10)

    data = main_error_data.get(category, [])
    if not data:
        tk.Label(detail_frame, text="No fault data found.", font=("Arial", 10), bg="white").pack()
    else:
        for item in data:
            text = f"Machine: {item['machine']}, Field: {item['field_no']}, Code: {item['code']}"
            tk.Label(detail_frame, text=text, anchor="w", font=("Arial", 10), bg="white").pack(fill="x", padx=10)
