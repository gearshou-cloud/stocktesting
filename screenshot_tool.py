import tkinter as tk
from tkinter import ttk, messagebox
import pyvisa
import os
from datetime import datetime
from PIL import Image, ImageTk
import io

class ChannelFrame(ttk.LabelFrame):
    def __init__(self, parent, channel_num, command_callback):
        super().__init__(parent, text=f"Channel Setting {channel_num}")
        self.channel_num = channel_num
        self.command_callback = command_callback
        self.create_widgets()

    def create_widgets(self):
        # Grid layout for the channel settings
        
        # Channel Enable/Select
        ttk.Label(self, text="Channel").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.channel_var = tk.StringVar(value=str(self.channel_num))
        # Disabled entry for channel number
        ttk.Entry(self, textvariable=self.channel_var, width=10, state="disabled").grid(row=0, column=1, padx=5, pady=2)

        # Vertical Scale
        ttk.Label(self, text="Vertical Scale (per div)").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.scale_var = tk.StringVar(value="0.1")
        scale_entry = ttk.Entry(self, textvariable=self.scale_var, width=10)
        scale_entry.grid(row=1, column=1, padx=5, pady=2)
        scale_entry.bind('<Return>', lambda e: self.send_command("SCALE", self.scale_var.get()))
        # Offset
        ttk.Label(self, text="Offset").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.offset_var = tk.StringVar(value="0.0")
        offset_entry = ttk.Entry(self, textvariable=self.offset_var, width=10)
        offset_entry.grid(row=2, column=1, padx=5, pady=2)
        offset_entry.bind('<Return>', lambda e: self.send_command("OFFSET", self.offset_var.get()))

        # Coupling
        ttk.Label(self, text="Coupling").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.coupling_var = tk.StringVar(value="DC (50Ω)")
        coupling_cb = ttk.Combobox(self, textvariable=self.coupling_var, 
                                 values=["DC (50Ω)", "DC (1MΩ)", "AC", "GND"], width=10)
        coupling_cb.grid(row=3, column=1, padx=5, pady=2)
        coupling_cb.bind('<<ComboboxSelected>>', lambda e: self.send_command("COUPLING", self.coupling_var.get()))

        # Label (Not a critical SCPI usually, just UI for now or display:TEXT)
        ttk.Label(self, text="Label").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.label_var = tk.StringVar(value=f"Ch{self.channel_num}")
        label_entry = ttk.Entry(self, textvariable=self.label_var, width=10)
        label_entry.grid(row=4, column=1, padx=5, pady=2)
        label_entry.bind('<Return>', lambda e: self.send_command("LABEL", self.label_var.get()))

    def send_command(self, cmd_type, value):
        if self.command_callback:
            self.command_callback(self.channel_num, cmd_type, value)

    def update_channel_num(self, new_num):
        self.channel_num = new_num
        self.configure(text=f"Channel Setting {new_num}")
        self.channel_var.set(str(new_num))
        self.label_var.set(f"Ch{new_num}")


class ScreenshotTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Oscilloscope Remote Control")
        self.root.geometry("1400x900")
        
        # Initialize VISA
        self.rm = pyvisa.ResourceManager()
        self.scope = None
        self.is_running = True  # Track run/stop state locally
        
        # Auto-update waveform settings
        self.auto_update_enabled = False
        self.update_interval = 1000  # milliseconds
        self.update_timer = None
        
        # Style configuration
        style = ttk.Style()
        style.configure("Green.TButton", background="green", foreground="black", font=("Arial", 12, "bold"))
        
        self.create_main_layout()

    def create_main_layout(self):
        # Main container: Split into Left (Controls) and Right (Display)
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- LEFT PANEL: CONTROLS ---
        # Create a frame with scrollbar for left panel
        left_container = ttk.Frame(main_paned, width=350)
        main_paned.add(left_container)
        
        # Add scrollbar
        left_scrollbar = ttk.Scrollbar(left_container, orient=tk.VERTICAL)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for scrolling
        left_canvas = tk.Canvas(left_container, yscrollcommand=left_scrollbar.set, highlightthickness=0)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.config(command=left_canvas.yview)
        
        # Create frame inside canvas
        left_frame = ttk.Frame(left_canvas)
        canvas_window = left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        
        # Configure canvas scrolling
        def configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        left_frame.bind("<Configure>", configure_scroll_region)
        
        # Bind mousewheel
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # 1. Top Control Block (Run/Stop, Auto-Set)
        top_ctrl_frame = ttk.Frame(left_frame)
        top_ctrl_frame.pack(fill=tk.X, pady=10)
        
        # Run/Stop Button
        self.run_btn = tk.Button(top_ctrl_frame, text="RUNNING", bg="green", font=("Arial", 14, "bold"), height=2, command=self.toggle_run_stop)
        self.run_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Auto-Set Button
        self.autoset_btn = ttk.Button(top_ctrl_frame, text="Auto-Set", command=self.auto_set)
        self.autoset_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Time Scale
        time_frame = ttk.LabelFrame(left_frame, text="Time Scale")
        time_frame.pack(fill=tk.X, pady=5, padx=5)
        self.time_scale_var = tk.StringVar(value="100us")
        ttk.Entry(time_frame, textvariable=self.time_scale_var).pack(fill=tk.X, padx=5, pady=5)

        # Connection / System Settings (Mini)
        conn_frame = ttk.LabelFrame(left_frame, text="System Connection")
        conn_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(conn_frame, text="IP Address:").pack(anchor="w", padx=5)
        self.ip_entry = ttk.Entry(conn_frame)
        self.ip_entry.insert(0, "169.254.191.223")
        self.ip_entry.pack(fill=tk.X, padx=5, pady=2)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_scope)
        self.connect_btn.pack(fill=tk.X, padx=5, pady=5)
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.pack(anchor="w", padx=5)
        
        # --- NEW: Channel Toggles (Ch1 - Ch8) ---
        toggle_frame = ttk.LabelFrame(left_frame, text="Channel Enable (Click to Toggle)")
        toggle_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Grid for 8 small buttons
        self.ch_toggles = {}
        for i in range(8):
            ch_num = i + 1
            btn = tk.Button(toggle_frame, text=f"Ch{ch_num}", width=5, 
                            bg="lightgray", 
                            command=lambda n=ch_num: self.toggle_channel(n))
            btn.grid(row=i//4, column=i%4, padx=2, pady=2, sticky="ew")
            self.ch_toggles[ch_num] = btn

        # --- NEW: Single Active Channel Control ---
        ctrl_container = ttk.LabelFrame(left_frame, text="Active Channel Setting")
        ctrl_container.pack(fill=tk.X, pady=10, padx=5)
        
        # Channel Selector
        sel_frame = ttk.Frame(ctrl_container)
        sel_frame.pack(fill=tk.X, pady=5)
        ttk.Label(sel_frame, text="Select Channel to Control:").pack(side=tk.LEFT, padx=5)
        self.selected_channel_var = tk.StringVar(value="1")
        chan_selector = ttk.Combobox(sel_frame, textvariable=self.selected_channel_var, 
                                     values=[str(i) for i in range(1, 9)], width=5, state="readonly")
        chan_selector.pack(side=tk.LEFT, padx=5)
        chan_selector.bind('<<ComboboxSelected>>', self.on_channel_selection_change)
        
        # Reuse ChannelFrame logic but purely for controls
        self.active_channel_frame = ChannelFrame(ctrl_container, 1, self.handle_channel_command)
        self.active_channel_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Link selector to the frame
        self.selected_channel_var.trace("w", self.update_control_panel_target)

        # Add Actions
        action_frame = ttk.LabelFrame(left_frame, text="Actions")
        action_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Auto-update toggle
        self.auto_update_btn = tk.Button(action_frame, text="Auto-Update: OFF", bg="lightgray", 
                                         font=("Arial", 10, "bold"), command=self.toggle_auto_update)
        self.auto_update_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Update interval setting
        interval_frame = ttk.Frame(action_frame)
        interval_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(interval_frame, text="Update Interval (ms):").pack(side=tk.LEFT, padx=2)
        self.interval_var = tk.StringVar(value="1000")
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=8)
        interval_entry.pack(side=tk.LEFT, padx=2)
        interval_entry.bind('<Return>', lambda e: self.update_interval_setting())
        
        
        ttk.Button(action_frame, text="Update Measurements", command=self.update_measurements).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(action_frame, text="Capture Screenshot", command=self.capture_screenshot).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(action_frame, text="Fetch from Memory", command=self.fetch_memory).pack(fill=tk.X, padx=5, pady=2)
        
        # Mask control buttons
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(action_frame, text="Mask Test:", font=("Arial", 9, "bold")).pack(anchor="w", padx=5)
        
        # Mask channel selector
        mask_ch_frame = ttk.Frame(action_frame)
        mask_ch_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(mask_ch_frame, text="Channel:").pack(side=tk.LEFT, padx=2)
        self.mask_channel_var = tk.StringVar(value="C1")
        mask_ch_combo = ttk.Combobox(mask_ch_frame, textvariable=self.mask_channel_var,
                                     values=["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
                                     width=5, state="readonly")
        mask_ch_combo.pack(side=tk.LEFT, padx=2)
        
        # Upper tolerance
        upper_frame = ttk.Frame(action_frame)
        upper_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(upper_frame, text="Upper (%):").pack(side=tk.LEFT, padx=2)
        self.mask_upper_var = tk.StringVar(value="10")
        ttk.Entry(upper_frame, textvariable=self.mask_upper_var, width=8).pack(side=tk.LEFT, padx=2)
        
        # Lower tolerance
        lower_frame = ttk.Frame(action_frame)
        lower_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(lower_frame, text="Lower (%):").pack(side=tk.LEFT, padx=2)
        self.mask_lower_var = tk.StringVar(value="10")
        ttk.Entry(lower_frame, textvariable=self.mask_lower_var, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="Add Mask", command=self.add_mask).pack(fill=tk.X, padx=5, pady=2)
        
        # Mask enable toggle
        self.mask_enabled = False
        self.mask_toggle_btn = tk.Button(action_frame, text="Mask Test: OFF", bg="lightgray",
                                         font=("Arial", 10, "bold"), command=self.toggle_mask)
        self.mask_toggle_btn.pack(fill=tk.X, padx=5, pady=2)



        # --- RIGHT PANEL: DISPLAY ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame)
        
        # File Path Bar
        path_frame = ttk.Frame(right_frame)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="Filepath:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Image Display Area
        self.img_canvas_frame = ttk.Frame(right_frame, relief="sunken", borderwidth=1)
        self.img_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_label = ttk.Label(self.img_canvas_frame, text="No Image")
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # Measurement Table
        self.create_measurement_table(right_frame)

    def create_measurement_table(self, parent):
        table_frame = ttk.Frame(parent, height=200)
        table_frame.pack(fill=tk.X, padx=5, pady=5)
        
        cols = ("Measure", "Current")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=5)
        
        # Set column widths
        self.tree.heading("Measure", text="Measure")
        self.tree.column("Measure", width=150, anchor="w")
        self.tree.heading("Current", text="Current")
        self.tree.column("Current", width=120, anchor="center")
            
        # Measurement data will be populated from scope
        # Store tree item IDs for updating
        self.measurement_items = {}
            
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Logic ---

    def connect_scope(self):
        ip = self.ip_entry.get()
        try:
            resource = f"TCPIP0::{ip}::INSTR"
            self.scope = self.rm.open_resource(resource)
            self.scope.timeout = 5000
            idn = self.scope.query("*IDN?")
            self.status_label.config(text=f"Connected: {idn[:20]}...", foreground="green")
            messagebox.showinfo("Success", f"Connected to {idn}")
            
            # Auto-configure measurements for Channel 1 and 2 PDelta
            self.setup_default_measurements()
        except Exception as e:
            self.status_label.config(text="Connection Failed", foreground="red")
            messagebox.showerror("Error", str(e))
    
    def setup_default_measurements(self):
        """Setup default measurements: Ch1 and Ch2 PDelta"""
        if not self.scope:
            return
        
        try:
            # First, ensure Channel 1 and 2 are enabled
            self.scope.write("CHANnel1:STATe ON")
            self.scope.write("CHANnel2:STATe ON")
            print("Enabled Channel 1 and 2")
            
            # Enable Statistics for all measurements (required to get AVG, PPEak, NPEak, etc.)
            self.scope.write("MEASurement1:STATistics:ENABle ON")
            print("Enabled Statistics")
            
            # Configure MEASurement1 for Channel 1 Amplitude (Peak-to-Peak)
            # Based on MXO5 SCPI documentation
            
            # Measurement 1: Channel 1 Amplitude (PTP)
            self.scope.write("MEASurement1:SOURce C1")
            self.scope.write("MEASurement1:MAIN AMPLitude")
            self.scope.write("MEASurement1:ENABle ON")
            
            # Verify measurement 1 is enabled
            meas1_enabled = self.scope.query("MEASurement1:ENABle?").strip()
            print(f"Configured MEASurement1: Ch1 Amplitude (Enabled: {meas1_enabled})")
            
            # Measurement 2: Channel 2 Amplitude (PTP)
            self.scope.write("MEASurement2:SOURce C2")
            self.scope.write("MEASurement2:MAIN AMPLitude")
            self.scope.write("MEASurement2:ENABle ON")
            
            # Verify measurement 2 is enabled
            meas2_enabled = self.scope.query("MEASurement2:ENABle?").strip()
            print(f"Configured MEASurement2: Ch2 Amplitude (Enabled: {meas2_enabled})")
            
            # Update the channel toggle button colors
            if hasattr(self, 'ch_toggles'):
                self.ch_toggles[1].config(bg="green")
                self.ch_toggles[2].config(bg="green")
            
        except Exception as e:
            print(f"Error setting up default measurements: {e}")

    def toggle_run_stop(self):
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return

        try:
            # Toggle local state
            self.is_running = not self.is_running
            
            if self.is_running:
                self.scope.write(":RUN")
                self.run_btn.config(background="green", text="RUNNING")
                print("Sent :RUN")
            else:
                self.scope.write(":STOP")
                self.run_btn.config(background="red", text="STOPPED")
                print("Sent :STOP")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle Run/Stop: {e}")


    def auto_set(self):
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
            
        try:
            print("Sending Auto-Set command...")
            self.scope.write(":AUTOSCALE")
            messagebox.showinfo("Success", "Auto-Set command sent (:AUTOSCALE)")
        except Exception as e:
            messagebox.showerror("Error", f"Auto-Set failed: {e}")

    def add_mask(self):
        """Add a mask test based on current waveform with user-defined tolerance"""
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
        
        try:
            # Get user settings
            channel = self.mask_channel_var.get()
            upper_tolerance = float(self.mask_upper_var.get()) / 100.0  # Convert % to decimal
            lower_tolerance = float(self.mask_lower_var.get()) / 100.0
            
            print(f"Creating mask for {channel} with Upper: {upper_tolerance*100}%, Lower: {lower_tolerance*100}%")
            
            # Step 1: Add mask test
            self.scope.write("MTESt1:ADD")
            self.scope.write(f"MTESt1:SOURce {channel}")
            
            # Step 2: Get waveform data from the channel
            # Set data format to ASCII for easier parsing
            self.scope.write("FORMat:DATA ASCii")
            
            # Get waveform preamble (contains scale info)
            preamble = self.scope.query(f"{channel}:DATA:HEADer?")
            print(f"Waveform header: {preamble}")
            
            # Get waveform data points (simplified - get fewer points for mask)
            # Query a subset of points to create a manageable mask
            waveform_data = self.scope.query(f"{channel}:DATA:VALues? 0,100")  # Get 100 points
            
            # Parse waveform data
            values = [float(v) for v in waveform_data.strip().split(',')]
            print(f"Got {len(values)} waveform points")
            
            # Get time scale info
            time_scale = float(self.scope.query("TIMebase:SCALe?"))
            time_position = float(self.scope.query("TIMebase:POSition?"))
            
            # Calculate time points
            num_points = len(values)
            time_range = time_scale * 10  # 10 divisions
            time_start = time_position - time_range / 2
            time_step = time_range / num_points
            
            # Step 3: Create upper mask segment
            self.scope.write("MTESt1:SEGMent1:ADD")
            
            # Add points for upper boundary
            for i, value in enumerate(values):
                time_point = time_start + i * time_step
                upper_value = value * (1 + upper_tolerance)
                
                self.scope.write(f"MTESt1:SEGMent1:POINt{i+1}:ADD")
                self.scope.write(f"MTESt1:SEGMent1:POINt{i+1}:X {time_point}")
                self.scope.write(f"MTESt1:SEGMent1:POINt{i+1}:Y {upper_value}")
            
            # Step 4: Create lower mask segment
            self.scope.write("MTESt1:SEGMent2:ADD")
            
            # Add points for lower boundary
            for i, value in enumerate(values):
                time_point = time_start + i * time_step
                lower_value = value * (1 - lower_tolerance)
                
                self.scope.write(f"MTESt1:SEGMent2:POINt{i+1}:ADD")
                self.scope.write(f"MTESt1:SEGMent2:POINt{i+1}:X {time_point}")
                self.scope.write(f"MTESt1:SEGMent2:POINt{i+1}:Y {lower_value}")
            
            # Make mask visible
            self.scope.write("MTESt1:VISible ON")
            
            # Wait for operation to complete
            self.scope.query("*OPC?")
            
            messagebox.showinfo("Success", 
                              f"Mask created for {channel}\n"
                              f"Upper tolerance: {upper_tolerance*100}%\n"
                              f"Lower tolerance: {lower_tolerance*100}%\n"
                              f"Points: {num_points}")
            print(f"Mask test 1 created successfully with {num_points} points per segment")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid tolerance values. Please enter numbers.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add mask: {e}")
            print(f"Error adding mask: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_mask(self):
        """Toggle mask test on/off"""
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
        
        try:
            self.mask_enabled = not self.mask_enabled
            
            if self.mask_enabled:
                # Enable mask test 1
                self.scope.write("MTESt1:STATe ON")
                self.mask_toggle_btn.config(text="Mask Test: ON", bg="green")
                print("Mask test enabled")
            else:
                # Disable mask test 1
                self.scope.write("MTESt1:STATe OFF")
                self.mask_toggle_btn.config(text="Mask Test: OFF", bg="lightgray")
                print("Mask test disabled")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle mask: {e}")
            print(f"Error toggling mask: {e}")

    def toggle_auto_update(self):
        """Toggle auto-update waveform on/off"""
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
        
        self.auto_update_enabled = not self.auto_update_enabled
        
        if self.auto_update_enabled:
            self.auto_update_btn.config(text="Auto-Update: ON", bg="green")
            self.start_auto_update()
            print("Auto-update enabled")
        else:
            self.auto_update_btn.config(text="Auto-Update: OFF", bg="lightgray")
            self.stop_auto_update()
            print("Auto-update disabled")
    
    def update_interval_setting(self):
        """Update the auto-update interval"""
        try:
            new_interval = int(self.interval_var.get())
            if new_interval < 100:
                messagebox.showwarning("Warning", "Interval too short, minimum is 100ms")
                self.interval_var.set("100")
                new_interval = 100
            self.update_interval = new_interval
            print(f"Update interval set to {new_interval}ms")
            
            # Restart timer if auto-update is running
            if self.auto_update_enabled:
                self.stop_auto_update()
                self.start_auto_update()
        except ValueError:
            messagebox.showerror("Error", "Invalid interval value")
            self.interval_var.set(str(self.update_interval))
    
    def start_auto_update(self):
        """Start the auto-update timer"""
        self.auto_update_waveform()
    
    def stop_auto_update(self):
        """Stop the auto-update timer"""
        if self.update_timer:
            self.root.after_cancel(self.update_timer)
            self.update_timer = None
    
    def auto_update_waveform(self):
        """Automatically capture and update waveform"""
        if not self.auto_update_enabled or not self.scope:
            return
        
        try:
            # Capture screenshot without showing success message
            self.capture_screenshot_silent()
            # Update measurement data
            self.update_measurements()
        except Exception as e:
            print(f"Auto-update error: {e}")
        
        # Schedule next update
        if self.auto_update_enabled:
            self.update_timer = self.root.after(self.update_interval, self.auto_update_waveform)

    def update_measurements(self):
        """Update measurement table with data from scope"""
        if not self.scope:
            return
        
        # Save original timeout and set a shorter one for measurement updates
        original_timeout = self.scope.timeout
        self.scope.timeout = 2000  # 2 seconds timeout for faster response
        
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.measurement_items.clear()
            
            # Only check first 8 measurements to avoid timeout issues
            # Most users won't configure more than 8 measurements anyway
            
            for meas_num in range(1, 9):  # Check measurements 1-8
                try:
                    # Check if measurement is enabled with shorter timeout
                    enabled = self.scope.query(f"MEASurement{meas_num}:ENABle?").strip()
                    if enabled != "1" and enabled.upper() != "ON":
                        continue
                    
                    # Get the measurement type
                    meas_type = self.scope.query(f"MEASurement{meas_num}:MAIN?").strip()
                    
                    if not meas_type or meas_type == "NONE":
                        continue
                    
                    # Get measurement results - only Current value
                    # ACTual = current value
                    try:
                        current = self.scope.query(f"MEASurement{meas_num}:RESult:ACTual?").strip()
                    except:
                        current = "N/A"
                    
                    
                    # Get the source channel for better display
                    try:
                        source = self.scope.query(f"MEASurement{meas_num}:SOURce?").strip()
                    except:
                        source = "?"
                    
                    # Format the measurement name with channel info
                    # Example: "M1: Ch1 PDelta" instead of "1 PDEL"
                    meas_name = f"M{meas_num}: {source} {meas_type}"

                    
                    # Format current value with units
                    try:
                        current_fmt = self.format_measurement_value(current) if current != "N/A" else "N/A"
                    except Exception as e:
                        print(f"Error formatting value for MEASurement{meas_num}: {e}")
                        current_fmt = current
                    
                    # Insert into tree (only Measure and Current columns)
                    try:
                        item_id = self.tree.insert("", "end", values=(meas_name, current_fmt))
                        self.measurement_items[meas_num] = item_id
                        print(f"Updated measurement {meas_num}: {meas_type} = {current_fmt}")
                    except Exception as e:
                        print(f"Error inserting MEASurement{meas_num} into table: {e}")
                    
                except Exception as e:
                    # Skip this measurement if there's any error
                    # Don't print timeout errors to reduce console spam
                    if "TMO" not in str(e):
                        print(f"Error reading MEASurement{meas_num}: {e}")
                    continue
            
            print("Measurement update completed")
                    
        except Exception as e:
            print(f"Error updating measurements: {e}")
        finally:
            # Restore original timeout
            self.scope.timeout = original_timeout
    
    def format_measurement_value(self, value):
        """Format measurement value with appropriate units"""
        try:
            val = float(value)
            
            # Auto-scale to appropriate unit
            if abs(val) >= 1:
                return f"{val:.3f}"
            elif abs(val) >= 1e-3:
                return f"{val*1e3:.3f} m"
            elif abs(val) >= 1e-6:
                return f"{val*1e6:.3f} µ"
            elif abs(val) >= 1e-9:
                return f"{val*1e9:.3f} n"
            elif abs(val) >= 1e-12:
                return f"{val*1e12:.3f} p"
            else:
                return f"{val:.3e}"
        except:
            return value



    def toggle_channel(self, channel_num):
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
            
        try:
            try:
                state = self.scope.query(f"CHANnel{channel_num}:STATe?").strip().upper()
            except:
                state = "OFF"
                
            new_state = "ON" if state == "OFF" or state == "0" else "OFF"
            self.scope.write(f"CHANnel{channel_num}:STATe {new_state}")
            print(f"Set Ch{channel_num} to {new_state}")
            
            color = "green" if new_state == "ON" else "lightgray"
            self.ch_toggles[channel_num].config(bg=color)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle Ch{channel_num}: {e}")

    def on_channel_selection_change(self, event):
        self.update_control_panel_target()

    def update_control_panel_target(self, *args):
        try:
            new_ch = int(self.selected_channel_var.get())
            self.active_channel_frame.update_channel_num(new_ch)
        except ValueError:
            pass

    def handle_channel_command(self, channel_num, cmd_type, value):
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
            
        try:
            command = ""
            if cmd_type == "SCALE":
                command = f"CHANnel{channel_num}:SCALe {value}"
            elif cmd_type == "OFFSET":
                command = f"CHANnel{channel_num}:OFFSet {value}"
            elif cmd_type == "COUPLING":
                scpi_val = value
                if "50Ω" in value:
                    scpi_val = "DC"
                elif "1MΩ" in value:
                    scpi_val = "DCLimit"
                
                command = f"CHANnel{channel_num}:COUPling {scpi_val}"
            elif cmd_type == "LABEL":
                # Use DISPlay:SIGNal:LABel command
                command = f"DISPlay:SIGNal:LABel C{channel_num},'{value}'"
            
            if command:
                print(f"Sending: {command}")
                self.scope.write(command)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set {cmd_type}: {e}")

    def capture_screenshot(self):
        if not self.scope:
            messagebox.showerror("Error", "Not Connected")
            return
            
        try:
            self.scope.write("HCOP:DEV:LANG PNG")
            self.scope.write("HCOP:DEST MMEM")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scr_{timestamp}.png"
            self.scope.write(f"MMEM:NAME '{filename}'")
            self.scope.write("HCOP:IMMediate")
            self.scope.query("*OPC?")
            self.transfer_file(filename)
        except Exception as e:
            messagebox.showerror("Error", f"Capture failed: {e}")

    def capture_screenshot_silent(self):
        """Capture screenshot without showing error dialogs (for auto-update)"""
        if not self.scope:
            return
            
        try:
            self.scope.write("HCOP:DEV:LANG PNG")
            self.scope.write("HCOP:DEST MMEM")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scr_{timestamp}.png"
            self.scope.write(f"MMEM:NAME '{filename}'")
            self.scope.write("HCOP:IMMediate")
            self.scope.query("*OPC?")
            self.transfer_file(filename)
        except Exception as e:
            print(f"Capture failed: {e}")


    def fetch_memory(self):
        pass

    def transfer_file(self, filename):
        try:
            scope_path = f"/home/storage/userData/screenshots/{filename}"
            self.scope.write(f'MMEM:DATA? "{scope_path}"')
            data = self.scope.read_raw()
            if data.startswith(b'#'):
                digits = int(chr(data[1]))
                img_data = data[2+digits:]
                local_path = os.path.abspath(os.path.join("screenshots", filename))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                if img_data.endswith(b'\n'):
                    img_data = img_data[:-1]
                with open(local_path, "wb") as f:
                    f.write(img_data)
                self.display_image(local_path)
                self.path_var.set(local_path)
        except Exception as e:
            print(f"Transfer error: {e}")

    def display_image(self, path):
        try:
            img = Image.open(path)
            w, h = img.size
            aspect = w / h
            target_h = 500
            target_w = int(target_h * aspect)
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=self.photo, text="")
        except Exception as e:
            self.image_label.configure(text=f"Error loading image: {e}")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Clean up before closing"""
        self.stop_auto_update()
        self.root.destroy()

if __name__ == "__main__":
    app = ScreenshotTool()
    app.run()