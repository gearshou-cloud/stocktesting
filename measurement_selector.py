import tkinter as tk
from tkinter import ttk, simpledialog
import pyvisa
import json

class MeasurementSelector:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.scope = None
        self.root = tk.Tk()
        self.root.title("示波器測量配置")
        self.root.geometry("900x500")
        self.measurement_items = self.load_measurement_items()
        self.active_channels = ["C1"]
        self.rows = []  # 每行: {'source_var':..., 'meas_var':..., 'meas_btn':...}
        self.create_connection_section()
        self.create_table_section()
        self.create_apply_section()
        self.load_config()  # 啟動時自動載入設定

    def load_measurement_items(self):
        with open('measurement_items.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['measurements']

    def save_config(self):
        config = []
        for row in self.rows:
            config.append({
                'source': row['source_var'].get(),
                'measurements': row['meas_var'].get(),
                'track': row['track_var'].get()
            })
        with open('measurement_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self):
        try:
            with open('measurement_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            for i, row_cfg in enumerate(config):
                if i < len(self.rows):
                    if row_cfg.get('source') in self.active_channels:
                        self.rows[i]['source_var'].set(row_cfg.get('source'))
                    self.rows[i]['meas_var'].set(row_cfg.get('measurements', ''))
                    if 'track' in row_cfg:
                        self.rows[i]['track_var'].set(row_cfg['track'])
        except Exception:
            pass

    def create_connection_section(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text="IP地址:").pack(side=tk.LEFT)
        self.ip_entry = ttk.Entry(frame)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "169.254.139.147")
        self.connect_btn = ttk.Button(frame, text="連接", command=self.connect_scope)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        self.scan_btn = ttk.Button(frame, text="掃描通道", command=self.scan_channels)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        self.result_label = ttk.Label(frame, text="未連接")
        self.result_label.pack(side=tk.LEFT, padx=10)

    def create_table_section(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側：測量配置表格和測量結果
        left_frame = ttk.Frame(self.main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
        
        # 左側上半部：配置表格和測量結果並排
        top_frame = ttk.Frame(left_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置表格（左）
        table_frame = ttk.LabelFrame(top_frame, text="測量配置 (最多10組)", padding="5")
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        header = ["#", "Source", "Measurement", "Track"]
        for col, text in enumerate(header):
            ttk.Label(table_frame, text=text, font=("Arial", 10, "bold")).grid(row=0, column=col, padx=2, pady=2)
        self.rows.clear()
        for i in range(10):
            row = {}
            ttk.Label(table_frame, text=str(i+1)).grid(row=i+1, column=0, padx=2)
            source_var = tk.StringVar(value=self.active_channels[0])
            source_combo = ttk.Combobox(table_frame, textvariable=source_var, values=self.active_channels, width=4, state="readonly")
            source_combo.grid(row=i+1, column=1, padx=2)
            row['source_var'] = source_var
            row['source_combo'] = source_combo
            meas_var = tk.StringVar(value="")
            meas_btn = ttk.Button(table_frame, text="選擇測項", command=lambda idx=i: self.choose_measurement(idx))
            meas_btn.grid(row=i+1, column=2, padx=2)
            row['meas_var'] = meas_var
            row['meas_btn'] = meas_btn
            row['meas_label'] = ttk.Label(table_frame, textvariable=meas_var, width=15, anchor="w")
            row['meas_label'].grid(row=i+1, column=3, padx=2)
            # Track勾選框
            track_var = tk.BooleanVar(value=False)
            track_check = ttk.Checkbutton(table_frame, variable=track_var)
            track_check.grid(row=i+1, column=4, padx=2)
            row['track_var'] = track_var
            self.rows.append(row)
            
        # 測量結果（右）
        self.create_result_area(top_frame)

        # 右側：NGP800設定和Generator/MASK設定
        right_frame = ttk.Frame(self.main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        
        # 右側上半部：NGP800相關設定
        top_frame = ttk.Frame(right_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # NGP800 連線區塊
        ngp_frame = ttk.LabelFrame(top_frame, text="NGP800 連線", padding="8")
        ngp_frame.pack(fill=tk.X, pady=10)
        ttk.Label(ngp_frame, text="IP地址:").grid(row=0, column=0, sticky="w")
        self.ngp_ip_entry = ttk.Entry(ngp_frame)
        self.ngp_ip_entry.grid(row=0, column=1, padx=5)
        self.ngp_ip_entry.insert(0, "169.254.139.148")
        self.ngp_connect_btn = ttk.Button(ngp_frame, text="連接", command=self.connect_ngp)
        self.ngp_connect_btn.grid(row=0, column=2, padx=5)
        
        # NGP800 設定區塊
        ngp_setting_frame = ttk.LabelFrame(top_frame, text="NGP800 設定", padding="8")
        ngp_setting_frame.pack(fill=tk.X, pady=10)
        ttk.Label(ngp_setting_frame, text="電壓 (V):").grid(row=0, column=0, sticky="w")
        self.ngp_voltage_var = tk.StringVar(value="12.0")
        ttk.Entry(ngp_setting_frame, textvariable=self.ngp_voltage_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(ngp_setting_frame, text="最大輸出電流 (A):").grid(row=1, column=0, sticky="w")
        self.ngp_current_var = tk.StringVar(value="5.0")
        ttk.Entry(ngp_setting_frame, textvariable=self.ngp_current_var, width=8).grid(row=1, column=1, padx=5)
        # 輸出按鈕
        self.ngp_output_btn = ttk.Button(ngp_setting_frame, text="輸出 OFF", command=self.toggle_ngp_output)
        self.ngp_output_btn.grid(row=2, column=0, columnspan=2, sticky="w", padx=5)
        self.ngp_output_state = False
        self.ngp_apply_btn = ttk.Button(ngp_setting_frame, text="Apply", command=self.apply_ngp_setting)
        self.ngp_apply_btn.grid(row=2, column=2, padx=5)
        
        # 右側下半部：Generator Setting和MASK設定並排
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Generator Setting（左）
        self.create_generator_setting(bottom_frame)
        # MASK 設定（右）
        self.create_mask_setting(bottom_frame)

    def create_generator_setting(self, parent):
        gen_frame = ttk.LabelFrame(parent, text="Generator Setting", padding="8")
        gen_frame.pack(fill=tk.X, pady=10)
        # Function Type
        ttk.Label(gen_frame, text="Function Type (Sine)").grid(row=0, column=0, sticky="w")
        self.gen_func_var = tk.StringVar(value="Sine")
        func_combo = ttk.Combobox(gen_frame, textvariable=self.gen_func_var, values=["Sine", "Square", "Triangle"], width=8, state="readonly")
        func_combo.grid(row=0, column=1, padx=5, pady=2)
        # Step Point
        ttk.Label(gen_frame, text="Step Point").grid(row=0, column=2, sticky="w")
        self.gen_step_var = tk.StringVar(value="3")
        ttk.Entry(gen_frame, textvariable=self.gen_step_var, width=8).grid(row=0, column=3, padx=5, pady=2)
        # Frequency Start/Stop
        ttk.Label(gen_frame, text="Frequency Start (Hz)").grid(row=1, column=0, sticky="w")
        self.gen_freq_start_var = tk.StringVar(value="800")
        ttk.Entry(gen_frame, textvariable=self.gen_freq_start_var, width=8).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(gen_frame, text="Frequency Stop (Hz)").grid(row=1, column=2, sticky="w")
        self.gen_freq_stop_var = tk.StringVar(value="1.2k")
        ttk.Entry(gen_frame, textvariable=self.gen_freq_stop_var, width=8).grid(row=1, column=3, padx=5, pady=2)
        # Duty Cycle Start/Stop
        ttk.Label(gen_frame, text="Duty Cycle Start (%)").grid(row=2, column=0, sticky="w")
        self.gen_duty_start_var = tk.StringVar(value="8.000")
        ttk.Entry(gen_frame, textvariable=self.gen_duty_start_var, width=8).grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(gen_frame, text="Duty Cycle Stop (%)").grid(row=2, column=2, sticky="w")
        self.gen_duty_stop_var = tk.StringVar(value="12.000")
        ttk.Entry(gen_frame, textvariable=self.gen_duty_stop_var, width=8).grid(row=2, column=3, padx=5, pady=2)
        # Amplitude
        ttk.Label(gen_frame, text="Amplitude").grid(row=3, column=0, sticky="w")
        self.gen_amp_var = tk.StringVar(value="5.000")
        ttk.Entry(gen_frame, textvariable=self.gen_amp_var, width=8).grid(row=3, column=1, padx=5, pady=2)
        # Offset
        ttk.Label(gen_frame, text="Offset").grid(row=3, column=2, sticky="w")
        self.gen_offset_var = tk.StringVar(value="2.500")
        ttk.Entry(gen_frame, textvariable=self.gen_offset_var, width=8).grid(row=3, column=3, padx=5, pady=2)

    def create_mask_setting(self, parent):
        mask_frame = ttk.LabelFrame(parent, text="MASK 設定", padding="8")
        mask_frame.pack(fill=tk.X, pady=10)
        # 基準電壓
        ttk.Label(mask_frame, text="基準電壓:").grid(row=0, column=0, sticky="w")
        self.mask_ref_voltage_var = tk.StringVar(value="12.0")
        ttk.Entry(mask_frame, textvariable=self.mask_ref_voltage_var, width=8).grid(row=0, column=1, padx=5)
        ttk.Label(mask_frame, text="V").grid(row=0, column=2, sticky="w")
        # 誤差
        ttk.Label(mask_frame, text="誤差:").grid(row=0, column=3, sticky="w")
        self.mask_tolerance_var = tk.StringVar(value="1.0")
        ttk.Entry(mask_frame, textvariable=self.mask_tolerance_var, width=8).grid(row=0, column=4, padx=5)
        ttk.Label(mask_frame, text="%").grid(row=0, column=5, sticky="w")
        # 通道
        ttk.Label(mask_frame, text="通道:").grid(row=1, column=0, sticky="w")
        self.mask_channel_var = tk.StringVar(value=self.active_channels[0])
        self.mask_channel_combo = ttk.Combobox(mask_frame, textvariable=self.mask_channel_var, values=self.active_channels, width=6, state="readonly")
        self.mask_channel_combo.grid(row=1, column=1, padx=5)
        # 設定MASK按鈕
        self.mask_btn = ttk.Button(mask_frame, text="設定MASK", command=self.setup_mask)
        self.mask_btn.grid(row=1, column=3, columnspan=2, padx=5, pady=5)

    def create_apply_section(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, pady=5)
        self.apply_btn = ttk.Button(frame, text="Apply", command=self.apply_measurements)
        self.apply_btn.pack(side=tk.LEFT, padx=10)
        self.result_label = ttk.Label(frame, text="")
        self.result_label.pack(side=tk.LEFT, padx=10)

    def scan_channels(self):
        if not self.scope:
            self.result_label.config(text="錯誤: 未連接示波器")
            return
        try:
            available_channels = []
            for i in range(1, 9):
                state = self.scope.query(f"CHANnel{i}:STATe?")
                if state.strip() == "1":
                    available_channels.append(f"C{i}")
            if not available_channels:
                available_channels = ["C1"]
            self.active_channels = available_channels
            for row in self.rows:
                row['source_combo']['values'] = self.active_channels
                if row['source_var'].get() not in self.active_channels:
                    row['source_var'].set(self.active_channels[0])
            self.result_label.config(text=f"已掃描到 {len(self.active_channels)} 個通道")
        except Exception as e:
            self.result_label.config(text=f"掃描通道失敗: {str(e)}")

    def connect_scope(self):
        try:
            ip = self.ip_entry.get()
            self.scope = self.rm.open_resource(f"TCPIP0::{ip}::INSTR")
            idn = self.scope.query("*IDN?")
            self.result_label.config(text=f"已連接: {idn}")
            self.scan_channels()
        except Exception as e:
            self.result_label.config(text=f"連接失敗: {str(e)}")

    def choose_measurement(self, idx):
        win = tk.Toplevel(self.root)
        win.title("選擇測項")
        win.geometry("350x400")
        win.transient(self.root)
        win.grab_set()
        check_vars = []
        row = 0
        selected_set = set([m.strip() for m in self.rows[idx]['meas_var'].get().split(',') if m.strip()])
        for item in self.measurement_items:
            var = tk.BooleanVar(value=(item['Meas_type'] in selected_set or item['Label'] in selected_set))
            chk = ttk.Checkbutton(win, text=item['Meas_type'], variable=var)
            chk.grid(row=row, column=0, sticky="w", padx=20)
            check_vars.append((item, var))
            row += 1
        def on_ok():
            selected = [item['Label'] for item, var in check_vars if var.get()]
            self.rows[idx]['meas_var'].set(", ".join(selected))
            win.destroy()
            self.save_config()
        ok_btn = ttk.Button(win, text="確定", command=on_ok)
        ok_btn.grid(row=row, column=0, pady=10)
        win.protocol("WM_DELETE_WINDOW", on_ok)

    def create_result_area(self, parent):
        result_frame = ttk.LabelFrame(parent, text="測量結果", padding="5")
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(5, 0), pady=5)
        self.result_canvas = tk.Canvas(result_frame, bg="#222", width=300, height=400, highlightthickness=0)
        self.result_canvas.pack(fill=tk.BOTH, expand=True)
        self.result_rows = []
        for i in range(10):
            y = 10 + i*38
            self.result_canvas.create_text(20, y+15, text=str(i+1), fill="white", font=("Arial", 11, "bold"), anchor="w", tags=f"row{i}_num")
            rect = self.result_canvas.create_rectangle(45, y, 75, y+30, fill="#444", outline="", tags=f"row{i}_rect")
            ch_text = self.result_canvas.create_text(60, y+15, text="", fill="black", font=("Arial", 11, "bold"), tags=f"row{i}_ch")
            meas_text = self.result_canvas.create_text(90, y+15, text="", fill="white", font=("Arial", 11), anchor="w", tags=f"row{i}_meas")
            val_text = self.result_canvas.create_text(250, y+15, text="", fill="white", font=("Arial", 11), anchor="e", tags=f"row{i}_val")
            self.result_rows.append((rect, ch_text, meas_text, val_text))
        self.update_result_btn = ttk.Button(result_frame, text="Update", command=self.update_result_area)
        self.update_result_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=8)
        self.update_result_area()

    def update_result_area(self):
        color_map = {
            'C1': '#ffe066', 'C2': '#7fff7f', 'C3': '#ffb366', 'C4': '#66b3ff',
            'C5': '#ff66b3', 'C6': '#b366ff', 'C7': '#b3ff66', 'C8': '#ff6666'
        }
        label_to_type = {item['Label']: item['Meas_type'] for item in self.measurement_items}
        for i, row in enumerate(self.rows):
            idx = i + 1
            ch = row['source_var'].get()
            meas_str = row['meas_var'].get()
            meas_label = meas_str.split(',')[0].strip() if meas_str else ''
            meas_type = label_to_type.get(meas_label, meas_label)
            color = color_map.get(ch, '#444')
            self.result_canvas.itemconfig(f"row{i}_rect", fill=color)
            self.result_canvas.itemconfig(f"row{i}_ch", text=ch)
            self.result_canvas.itemconfig(f"row{i}_meas", text=meas_type)
            val = ''
            if self.scope and ch and meas_label:
                try:
                    result = self.scope.query(f"MEASurement{idx}:RESult:ACTual?").strip()
                    try:
                        value = float(result)
                        if any(x in meas_type.lower() for x in ["time", "period", "rise", "fall", "width"]):
                            unit = "s"
                        elif any(x in meas_type.lower() for x in ["volt", "vpp", "high", "low", "amp"]):
                            unit = "V"
                        elif "freq" in meas_type.lower():
                            unit = "Hz"
                        else:
                            unit = ""
                        unit = unit if unit else ""
                        val = f"{value:.3g} {unit}".strip()
                    except ValueError:
                        val = result
                except Exception:
                    val = "N/A"
            self.result_canvas.itemconfig(f"row{i}_val", text=val)

    def apply_measurements(self):
        if not self.scope:
            self.result_label.config(text="錯誤: 未連接示波器")
            return
        try:
            self.scope.write("MEASurement:DELete:ALL")
            for i, row in enumerate(self.rows):
                idx = i + 1
                meas_str = row['meas_var'].get()
                source = row['source_var'].get()
                track = row['track_var'].get()
                if meas_str and source:
                    for label in [m.strip() for m in meas_str.split(',') if m.strip()]:
                        self.scope.write(f"MEASurement{idx}:ENABle ON")
                        self.scope.write(f"MEASurement{idx}:SOURce {source}")
                        self.scope.write(f"MEASurement{idx}:MAIN {label}")
                        # Track功能
                        if track:
                            self.scope.write(f"MEASurement{idx}:TRACk:STATe ON")
                        else:
                            self.scope.write(f"MEASurement{idx}:TRACk:STATe OFF")
                else:
                    self.scope.write(f"MEASurement{idx}:ENABle OFF")
            self.result_label.config(text="設定完成")
            self.save_config()
        except Exception as e:
            self.result_label.config(text=f"設定失敗: {str(e)}")

    def setup_mask(self):
        if not self.scope:
            self.result_label.config(text="錯誤: 未連接示波器")
            return
        try:
            # 先刪除所有現有的MASK
            try:
                mask_count = int(self.scope.query("MTES:COUNt?").strip())
            except Exception:
                mask_count = 0
            for m in range(mask_count, mask_count+1):
                print(f"MTESt{m}:REMove")
                self.scope.write(f"MTESt{m}:REMove")
            # 取得設定值
            ref_voltage = float(self.mask_ref_voltage_var.get())
            tolerance_percent = float(self.mask_tolerance_var.get()) / 100.0
            channel = self.mask_channel_var.get()
            tolerance_voltage = ref_voltage * tolerance_percent
            upper_limit = ref_voltage + tolerance_voltage
            lower_limit = ref_voltage - tolerance_voltage
            # 設定通道offset到基準電壓
            self.scope.write(f"{channel}:OFFSet {ref_voltage}")
            # 取得時間軸設定
            time_scale = float(self.scope.query("TIMebase:SCALe?"))
            time_left_edge = -5 * time_scale
            time_right_edge = 5 * time_scale
            # 取得垂直軸設定
            vertical_scale = float(self.scope.query(f"CHANnel{channel[1]}:SCALe?"))
            div_height = vertical_scale
            # 設置Mask測試區域
            self.scope.write("MTES:STATe ON")
            self.scope.write("MTES:COUNt:STATe ON")
            self.scope.write("MTES:RST")
            # 上界MASK
            self.scope.write("MTES:ADD")
            self.scope.write(f"MTES:MASK:SOURce {channel}")
            self.scope.write("MTES:SEGMent:ADD")
            for _ in range(4):
                self.scope.write("MTES:SEGMent:POINt:ADD")
            upper_points = [
                (time_left_edge, upper_limit + div_height),
                (time_right_edge, upper_limit + div_height),
                (time_right_edge, upper_limit),
                (time_left_edge, upper_limit)
            ]
            for i, (x, y) in enumerate(upper_points, 1):
                self.scope.write(f"MTES:SEGMent:POINt{i}:X {x}")
                self.scope.write(f"MTES:SEGMent:POINt{i}:Y {y}")
            # 下界MASK
            self.scope.write("MTES:ADD")
            self.scope.write(f"MTES:MASK:SOURce {channel}")
            self.scope.write("MTES:SEGMent:ADD")
            for _ in range(4):
                self.scope.write("MTES:SEGMent:POINt:ADD")
            lower_points = [
                (time_left_edge, lower_limit),
                (time_right_edge, lower_limit),
                (time_right_edge, lower_limit - div_height),
                (time_left_edge, lower_limit - div_height)
            ]
            for i, (x, y) in enumerate(lower_points, 1):
                self.scope.write(f"MTES:SEGMent:POINt{i}:X {x}")
                self.scope.write(f"MTES:SEGMent:POINt{i}:Y {y}")
            self.scope.write("MTES:COUNt:RESet:MODE TIME")
            self.scope.write("MTES:COUNt:RESet:TIME 1")
            self.scope.write("MTES:ACTion:STOP:STATe ON")
            self.scope.write("MTESt1:ONViolation:STOP SUCCess")
            self.scope.write("MTESt1:ONViolation:STOP VIOLation")
            self.result_label.config(text=f"MASK測試已設置: {ref_voltage}V ±{tolerance_percent*100}%")
        except Exception as e:
            self.result_label.config(text=f"設置MASK失敗: {str(e)}")

    def connect_ngp(self):
        try:
            ip = self.ngp_ip_entry.get()
            self.ngp = self.rm.open_resource(f"TCPIP0::{ip}::INSTR")
            idn = self.ngp.query("*IDN?")
            self.result_label.config(text=f"已連接NGP800: {idn}")
        except Exception as e:
            self.result_label.config(text=f"連接NGP800失敗: {str(e)}")

    def toggle_ngp_output(self):
        if not hasattr(self, 'ngp'):
            self.result_label.config(text="錯誤: 未連接NGP800")
            return
        try:
            self.ngp_output_state = not self.ngp_output_state
            output_state = "ON" if self.ngp_output_state else "OFF"
            self.ngp.write(f"OUTPut:STATe {output_state}")
            self.ngp_output_btn.config(text=f"輸出 {output_state}")
            self.result_label.config(text=f"NGP800輸出已{output_state}")
        except Exception as e:
            self.result_label.config(text=f"切換NGP800輸出失敗: {str(e)}")
            self.ngp_output_state = not self.ngp_output_state  # 恢復狀態

    def apply_ngp_setting(self):
        if not hasattr(self, 'ngp'):
            self.result_label.config(text="錯誤: 未連接NGP800")
            return
        try:
            voltage = float(self.ngp_voltage_var.get())
            current = float(self.ngp_current_var.get())
            self.ngp.write(f"SOURce:VOLTage {voltage}")
            self.ngp.write(f"SOURce:CURRent {current}")
            self.result_label.config(text=f"NGP800設定完成: {voltage}V, {current}A")
        except Exception as e:
            self.result_label.config(text=f"設定NGP800失敗: {str(e)}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MeasurementSelector()
    app.run() 