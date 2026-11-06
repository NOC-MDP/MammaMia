import sys
import numpy as np
import xarray as xr
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QSplitter, 
    QFileDialog, QComboBox, QGroupBox, QTabWidget, 
    QTableWidget, QTableWidgetItem, QMessageBox, QDateTimeEdit,
    QLineEdit, QCheckBox, QScrollArea, QFormLayout
)
from PyQt6.QtCore import Qt, QDateTime

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.figure import Figure
import cartopy.crs as ccrs
import cartopy.feature as cfeature


class MapCanvas(FigureCanvas):
    """Matplotlib canvas embedded in PyQt, configured for Cartopy North Polar Stereo."""
    def __init__(self, parent=None, width=5, height=5, dpi=100):
        self.proj = ccrs.NorthPolarStereo(central_longitude=0.0)
        
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection=self.proj)
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.init_map()
        
    def init_map(self):
        """Draws base map features for the Arctic region."""
        self.axes.set_extent([-180, 180, 60, 90], crs=ccrs.PlateCarree())
        
        self.axes.add_feature(cfeature.LAND, facecolor='#e0e0e0')
        self.axes.add_feature(cfeature.OCEAN, facecolor='#f0f8ff')
        self.axes.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='#333333')
        self.axes.gridlines(draw_labels=False, linestyle='--', color='gray', alpha=0.5)
        
        self.fig.tight_layout()


class ColorbarCanvas(FigureCanvas):
    """Dedicated compact canvas for rendering the colorbar legend in the left panel."""
    def __init__(self, parent=None, width=4, height=1.0, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_axes([0.15, 0.45, 0.75, 0.3])
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes.set_visible(False)
        self.fig.tight_layout()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Polar Toolbox - Mission & Trajectory Suite")
        self.resize(1400, 900)
        self.dtree = None  # Holds the xarray DataTree root
        self.plotted_collections = []  # Tracks multiple active scatter plots on Tab 1 map
        
        # Main Central Widget: QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Initialize Tabs
        self.init_tab1_viewer()
        self.init_tab2_generator()
        self.init_tab3_config()

    # =========================================================================
    # TAB 1: Payload Sensor Viewer
    # =========================================================================
    def init_tab1_viewer(self):
        tab1 = QWidget()
        main_layout = QHBoxLayout(tab1)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        
        dtree_group = QGroupBox("Campaign DataTree Navigation")
        dtree_layout = QVBoxLayout(dtree_group)
        
        self.open_dtree_btn = QPushButton("Open Campaign.zarr (DataTree)...")
        self.open_dtree_btn.clicked.connect(self.load_datatree)
        dtree_layout.addWidget(self.open_dtree_btn)
        
        dtree_layout.addWidget(QLabel("1. Select Mission Node:"))
        self.mission_combo = QComboBox()
        self.mission_combo.currentIndexChanged.connect(self.update_sensor_list)
        dtree_layout.addWidget(self.mission_combo)
        
        dtree_layout.addWidget(QLabel("2. Select Sensor Dataset (e.g., ctd):"))
        self.sensor_combo = QComboBox()
        self.sensor_combo.currentIndexChanged.connect(self.update_parameter_list)
        dtree_layout.addWidget(self.sensor_combo)
        
        dtree_layout.addWidget(QLabel("3. Select Parameter to Color-map:"))
        self.param_combo = QComboBox()
        dtree_layout.addWidget(self.param_combo)
        
        self.plot_btn = QPushButton("Plot Sensor Parameter on Map")
        self.plot_btn.clicked.connect(self.plot_sensor_parameter)
        dtree_layout.addWidget(self.plot_btn)
        
        self.clear_map_btn = QPushButton("Clear Map")
        self.clear_map_btn.clicked.connect(self.clear_map)
        dtree_layout.addWidget(self.clear_map_btn)
        
        control_layout.addWidget(dtree_group)
        
        control_layout.addWidget(QLabel("<b>Execution Log</b>"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        control_layout.addWidget(self.log_output)
        
        control_layout.addWidget(QLabel("<b>Colorbar Legend</b>"))
        self.cbar_canvas = ColorbarCanvas(self)
        control_layout.addWidget(self.cbar_canvas)
        
        splitter.addWidget(control_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.canvas = MapCanvas(self)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1000])
        
        self.tabs.addTab(tab1, "Payload Sensor Viewer")

    # =========================================================================
    # TAB 2: Trajectory Specification Generator
    # =========================================================================
    def init_tab2_generator(self):
        tab2 = QWidget()
        main_layout = QHBoxLayout(tab2)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        gen_control_panel = QWidget()
        gen_control_layout = QVBoxLayout(gen_control_panel)
        
        points_group = QGroupBox("Collated Waypoints & Timestamps")
        points_layout = QVBoxLayout(points_group)
        
        points_layout.addWidget(QLabel("Click points on the map to add coordinates:"))
        
        self.points_table = QTableWidget(0, 3)
        self.points_table.setHorizontalHeaderLabels(["Latitude (°N)", "Longitude (°E)", "Timestamp (UTC)"])
        self.points_table.horizontalHeader().setStretchLastSection(True)
        points_layout.addWidget(self.points_table)
        
        btn_layout = QHBoxLayout()
        self.remove_point_btn = QPushButton("Remove Selected")
        self.remove_point_btn.clicked.connect(self.remove_selected_waypoint)
        btn_layout.addWidget(self.remove_point_btn)
        
        self.clear_points_btn = QPushButton("Clear All")
        self.clear_points_btn.clicked.connect(self.clear_waypoints)
        btn_layout.addWidget(self.clear_points_btn)
        points_layout.addLayout(btn_layout)
        
        gen_control_layout.addWidget(points_group)
        
        datetime_group = QGroupBox("Default Waypoint Timestamp")
        datetime_layout = QVBoxLayout(datetime_group)
        
        datetime_layout.addWidget(QLabel("Base timestamp for newly clicked points:"))
        self.datetime_picker = QDateTimeEdit(QDateTime.currentDateTimeUtc())
        self.datetime_picker.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_picker.setCalendarPopup(True)
        datetime_layout.addWidget(self.datetime_picker)
        
        gen_control_layout.addWidget(datetime_group)
        
        splitter.addWidget(gen_control_panel)
        
        gen_right_panel = QWidget()
        gen_right_layout = QVBoxLayout(gen_right_panel)
        
        self.tab2_canvas = MapCanvas(self)
        self.tab2_toolbar = NavigationToolbar2QT(self.tab2_canvas, self)
        self.tab2_canvas.mpl_connect('button_press_event', self.handle_tab2_map_click)
        
        gen_right_layout.addWidget(self.tab2_toolbar)
        gen_right_layout.addWidget(self.tab2_canvas)
        
        splitter.addWidget(gen_right_panel)
        splitter.setSizes([450, 950])
        
        self.tabs.addTab(tab2, "Trajectory Waypoints")

    # =========================================================================
    # TAB 3: Mission Configuration & TOML Generator
    # =========================================================================
    def init_tab3_config(self):
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QLineEdit { min-width: 350px; padding: 4px; }")
        
        scroll_layout = QVBoxLayout(scroll_content)
        
        mission_group = QGroupBox("Mission Parameters")
        mission_form = QFormLayout(mission_group)
        
        self.input_mission_name = QLineEdit("polar argo_deployment")
        self.input_description = QLineEdit("Ten Polar Argo float deployment in Arctic Off Svalbard")
        self.input_mission_type = QLineEdit("example Polar campaign test case")
        self.input_depth_ini = QLineEdit("5.00")
        self.input_runtime = QLineEdit("365")
        self.input_timedelta = QLineEdit("15")
        self.input_output_timedelta = QLineEdit("15")
        self.input_output_file = QLineEdit("argo_float.zarr")
        self.input_overwrite = QCheckBox()
        self.input_overwrite.setChecked(True)
        
        mission_form.addRow("Mission Name:", self.input_mission_name)
        mission_form.addRow("Description:", self.input_description)
        mission_form.addRow("Mission Type:", self.input_mission_type)
        mission_form.addRow("Initial Depths (single or comma-sep):", self.input_depth_ini)
        mission_form.addRow("Runtime (days):", self.input_runtime)
        mission_form.addRow("Timedelta (min):", self.input_timedelta)
        mission_form.addRow("Output Timedelta (min):", self.input_output_timedelta)
        mission_form.addRow("Output File:", self.input_output_file)
        mission_form.addRow("Overwrite:", self.input_overwrite)
        
        scroll_layout.addWidget(mission_group)
        
        env_group = QGroupBox("Environment Extent")
        env_form = QFormLayout(env_group)
        
        self.input_lat_max = QLineEdit("90")
        self.input_lat_min = QLineEdit("60")
        self.input_lon_max = QLineEdit("180")
        self.input_lon_min = QLineEdit("-180")
        self.input_vert_max = QLineEdit("3000")
        self.input_time_start = QLineEdit("2025-02-02T12:00:00")
        self.input_time_end = QLineEdit("2026-04-04T12:00:00")
        
        env_form.addRow("Max Latitude:", self.input_lat_max)
        env_form.addRow("Min Latitude:", self.input_lat_min)
        env_form.addRow("Max Longitude:", self.input_lon_max)
        env_form.addRow("Min Longitude:", self.input_lon_min)
        env_form.addRow("Max Vertical:", self.input_vert_max)
        env_form.addRow("Coverage Start:", self.input_time_start)
        env_form.addRow("Coverage End:", self.input_time_end)
        
        scroll_layout.addWidget(env_group)
        
        sensor_group = QGroupBox("Sensors (ADCP)")
        sensor_form = QFormLayout(sensor_group)
        
        self.input_u_source = QLineEdit("cmems_mod_glo_phy-cur_anfc_0.083deg_P1M-m")
        self.input_u_var = QLineEdit("uo")
        self.input_v_source = QLineEdit("cmems_mod_glo_phy-cur_anfc_0.083deg_P1M-m")
        self.input_v_var = QLineEdit("vo")
        
        sensor_form.addRow("U-Velocity Source ID:", self.input_u_source)
        sensor_form.addRow("U-Velocity Variable:", self.input_u_var)
        sensor_form.addRow("V-Velocity Source ID:", self.input_v_source)
        sensor_form.addRow("V-Velocity Variable:", self.input_v_var)
        
        scroll_layout.addWidget(sensor_group)
        
        # --- 4. Kernel Parameters Group ---
        kernel_group = QGroupBox("Kernel Parameters")
        kernel_form = QFormLayout(kernel_group)
        
        self.input_mindepth = QLineEdit("1.0")
        self.input_driftdepth = QLineEdit("1000")
        self.input_maxdepth = QLineEdit("2000")
        self.input_v_speed = QLineEdit("0.10")
        self.input_cycletime = QLineEdit("864000")
        self.input_drifttime = QLineEdit("777600")
        self.input_kh_zonal = QLineEdit("100")
        self.input_kh_meridional = QLineEdit("100")
        self.input_dres = QLineEdit("0.0001")
        
        kernel_form.addRow("Min Depth (m):", self.input_mindepth)
        kernel_form.addRow("Drift Depth (m):", self.input_driftdepth)
        kernel_form.addRow("Max Depth (m):", self.input_maxdepth)
        kernel_form.addRow("Vertical Speed (m/s):", self.input_v_speed)
        kernel_form.addRow("Cycle Time (sec):", self.input_cycletime)
        kernel_form.addRow("Drift Time (sec):", self.input_drifttime)
        kernel_form.addRow("Kh Zonal (m²/s):", self.input_kh_zonal)
        kernel_form.addRow("Kh Meridional (m²/s):", self.input_kh_meridional)
        kernel_form.addRow("Dres:", self.input_dres)
        
        scroll_layout.addWidget(kernel_group)
        
        scroll.setWidget(scroll_content)
        tab3_layout.addWidget(scroll)
        
        gen_action_layout = QHBoxLayout()
        self.generate_toml_btn = QPushButton("Generate TOML Specification File")
        self.generate_toml_btn.setStyleSheet("background-color: #2b7a78; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        self.generate_toml_btn.clicked.connect(self.generate_toml_file)
        gen_action_layout.addWidget(self.generate_toml_btn)
        
        tab3_layout.addLayout(gen_action_layout)
        
        self.tabs.addTab(tab3, "Mission Configuration")

    # =========================================================================
    # Tab 1 Logic Methods
    # =========================================================================
    def load_datatree(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select Campaign.zarr Directory", "")
        if dir_name:
            try:
                self.dtree = xr.open_datatree(dir_name, engine="zarr")
                self.mission_combo.clear()
                
                valid_missions = []
                for name, node in self.dtree.children.items():
                    if 'payload' in node.children:
                        valid_missions.append(name)
                
                if valid_missions:
                    self.mission_combo.addItems(valid_missions)
                    self.log_output.append(f"Loaded DataTree successfully.\nFound mission nodes with payload: {valid_missions}")
                else:
                    self.log_output.append("DataTree opened, but no mission nodes containing a 'payload' node were found.")
            except Exception as e:
                self.log_output.append(f"Error reading DataTree store: {str(e)}")

    def update_sensor_list(self):
        self.sensor_combo.clear()
        mission_name = self.mission_combo.currentText()
        if not mission_name or self.dtree is None:
            return
            
        try:
            payload_node = self.dtree[mission_name]['payload']
            sensors = list(payload_node.children.keys())
            
            if sensors:
                self.sensor_combo.addItems(sensors)
                self.log_output.append(f"Mission '{mission_name}' payload sensors found: {sensors}")
            else:
                self.log_output.append(f"No sensor nodes found under payload for mission '{mission_name}'.")
        except Exception as e:
            self.log_output.append(f"Error loading sensors for mission '{mission_name}': {str(e)}")

    def update_parameter_list(self):
        self.param_combo.clear()
        mission_name = self.mission_combo.currentText()
        sensor_name = self.sensor_combo.currentText()
        
        if not mission_name or not sensor_name or self.dtree is None:
            return
            
        try:
            sensor_ds = self.dtree[mission_name]['payload'][sensor_name].ds
            if 'latitude' in sensor_ds and 'longitude' in sensor_ds:
                variables = list(sensor_ds.data_vars.keys())
                if variables:
                    self.param_combo.addItems([str(v) for v in variables])
                    self.log_output.append(f"Sensor '{sensor_name}' parameters found: {variables}")
                else:
                    self.log_output.append(f"Sensor dataset '{sensor_name}' contains no data variables.")
            else:
                self.log_output.append(f"Warning: Sensor dataset '{sensor_name}' is missing 'latitude' or 'longitude' dataarrays.")
        except Exception as e:
            self.log_output.append(f"Error loading parameters for sensor '{sensor_name}': {str(e)}")

    def plot_sensor_parameter(self):
        if self.dtree is None:
            self.log_output.append("No DataTree is currently loaded.")
            return
            
        mission_name = self.mission_combo.currentText()
        sensor_name = self.sensor_combo.currentText()
        param_name = self.param_combo.currentText()
        
        if not mission_name or not sensor_name or not param_name:
            self.log_output.append("Please select a mission, sensor, and parameter.")
            return
            
        try:
            sensor_ds = self.dtree[mission_name]['payload'][sensor_name].ds
            
            if 'latitude' not in sensor_ds or 'longitude' not in sensor_ds:
                self.log_output.append(f"Error: Sensor dataset '{sensor_name}' does not contain latitude/longitude arrays.")
                return
                
            lats = sensor_ds['latitude'].values
            lons = sensor_ds['longitude'].values
            values = sensor_ds[param_name].values
            
            sc = self.canvas.axes.scatter(
                lons, lats, 
                c=values, 
                cmap='viridis', 
                s=15, 
                transform=ccrs.PlateCarree(),
                label=f'{mission_name} / {sensor_name}: {param_name}'
            )
            
            self.plotted_collections.append(sc)
            
            self.cbar_canvas.axes.clear()
            self.cbar_canvas.axes.set_visible(True)
            cb = self.cbar_canvas.fig.colorbar(
                sc, 
                cax=self.cbar_canvas.axes, 
                orientation='horizontal'
            )
            cb.set_label(param_name, fontsize=9)
            cb.ax.tick_params(labelsize=8)
            self.cbar_canvas.fig.tight_layout()
            self.cbar_canvas.draw()
            
            self.canvas.axes.legend(loc='upper right', fontsize='small')
            self.canvas.draw()
            
            self.log_output.append(f"Added {len(lats)} points for '{param_name}' from sensor '{sensor_name}' ({mission_name}) to map.")
        except Exception as e:
            self.log_output.append(f"Error plotting parameter '{param_name}': {str(e)}")

    def clear_map(self):
        try:
            self.canvas.axes.clear()
            self.canvas.init_map()
            self.canvas.draw()
            
            self.plotted_collections.clear()
            
            self.cbar_canvas.axes.clear()
            self.cbar_canvas.axes.set_visible(False)
            self.cbar_canvas.draw()
            
            self.log_output.append("Cleared map canvas, active data collections, and colorbar legend.")
        except Exception as e:
            self.log_output.append(f"Error clearing map: {str(e)}")

    # =========================================================================
    # Tab 2 Logic Methods (Waypoint Collation & Date Picker)
    # =========================================================================
    def handle_tab2_map_click(self, event):
        if event.xdata is not None and event.ydata is not None:
            target_crs = ccrs.PlateCarree()
            transformed_coords = target_crs.transform_point(event.xdata, event.ydata, self.tab2_canvas.axes.projection)
            lon, lat = transformed_coords[0], transformed_coords[1]
            
            if 60 <= lat <= 90:
                dt_str = self.datetime_picker.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                
                row_position = self.points_table.rowCount()
                self.points_table.insertRow(row_position)
                self.points_table.setItem(row_position, 0, QTableWidgetItem(f"{lat:.4f}"))
                self.points_table.setItem(row_position, 1, QTableWidgetItem(f"{lon:.4f}"))
                self.points_table.setItem(row_position, 2, QTableWidgetItem(dt_str))
                
                self.tab2_canvas.axes.plot(
                    lon, lat,
                    marker='*',
                    color='crimson',
                    markersize=12,
                    transform=ccrs.PlateCarree()
                )
                self.tab2_canvas.draw()

    def remove_selected_waypoint(self):
        selected_rows = self.points_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        for index in sorted(selected_rows, reverse=True):
            self.points_table.removeRow(index.row())
        self.redraw_tab2_waypoints()

    def clear_waypoints(self):
        self.points_table.setRowCount(0)
        self.tab2_canvas.axes.clear()
        self.tab2_canvas.init_map()
        self.tab2_canvas.draw()

    def redraw_tab2_waypoints(self):
        self.tab2_canvas.axes.clear()
        self.tab2_canvas.init_map()
        
        lats, lons = [], []
        for row in range(self.points_table.rowCount()):
            lat = float(self.points_table.item(row, 0).text())
            lon = float(self.points_table.item(row, 1).text())
            lats.append(lat)
            lons.append(lon)
            
            self.tab2_canvas.axes.plot(
                lon, lat,
                marker='*',
                color='crimson',
                markersize=12,
                transform=ccrs.PlateCarree()
            )
            
        if lats and lons:
            self.tab2_canvas.axes.plot(
                lons, lats,
                color='orangered',
                linewidth=1.5,
                linestyle='--',
                transform=ccrs.PlateCarree()
            )
            
        self.tab2_canvas.draw()

    # =========================================================================
    # Tab 3 Logic Methods (TOML Generation with Depth Validation)
    # =========================================================================
    def generate_toml_file(self):
        """Compiles waypoints, validated depths, and parameters into a TOML file."""
        row_count = self.points_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, "No Waypoints", "Please add at least one waypoint in the 'Trajectory Waypoints' tab before generating.")
            return

        raw_depth_text = self.input_depth_ini.text().strip()
        try:
            depth_parts = [float(x.strip()) for x in raw_depth_text.split(",") if x.strip()]
        except ValueError:
            QMessageBox.warning(self, "Invalid Depth", "Please ensure initial depths are valid numbers separated by commas.")
            return
            
        if not depth_parts:
            QMessageBox.warning(self, "Invalid Depth", "Please specify at least one initial depth value.")
            return
            
        if len(depth_parts) == 1:
            depth_ini_list = [depth_parts[0]] * row_count
        elif len(depth_parts) == row_count:
            depth_ini_list = depth_parts
        else:
            QMessageBox.warning(
                self, 
                "Depth Count Mismatch", 
                f"The number of initial depths ({len(depth_parts)}) does not match the number of waypoint locations ({row_count}).\n"
                f"Please provide either 1 depth value (to apply to all locations) or exactly {row_count} depth values."
            )
            return

        lats, lons, datetimes = [], [], []
        for row in range(row_count):
            lats.append(float(self.points_table.item(row, 0).text()))
            lons.append(float(self.points_table.item(row, 1).text()))
            dt_raw = self.points_table.item(row, 2).text()
            dt_formatted = dt_raw.replace(" ", "T") + "Z" if not dt_raw.endswith("Z") else dt_raw
            datetimes.append(dt_formatted)

        file_path, _ = QFileDialog.getSaveFileName(self, "Save TOML Specification", "mission_spec.toml", "TOML Files (*.toml)")
        if not file_path:
            return

        try:
            toml_content = f"""[specification.mission_parameters]
mission_name = "{self.input_mission_name.text()}"
description = "{self.input_description.text()}"
mission_type = "{self.input_mission_type.text()}"
datetime_start = {datetimes}
lat_ini = {lats}
lon_ini = {lons}
depth_ini = {depth_ini_list}
runtime = {self.input_runtime.text()}
timedelta = {self.input_timedelta.text()}
output_timedelta = {self.input_output_timedelta.text()}
output_file = "{self.input_output_file.text()}"
overwrite = {str(self.input_overwrite.isChecked()).lower()}

[specification.environment.extent]
geospatial_lat_max = {self.input_lat_max.text()}
geospatial_lat_min = {self.input_lat_min.text()}
geospatial_lon_max = {self.input_lon_max.text()}
geospatial_lon_min = {self.input_lon_min.text()}
geospatial_vertical_max = {self.input_vert_max.text()}
time_coverage_start = "{self.input_time_start.text()}"
time_coverage_end = "{self.input_time_end.text()}"

[specification.sensors.adcp.u_velocity]
source_id = "{self.input_u_source.text()}"
variable_name = "{self.input_u_var.text()}"

[specification.sensors.adcp.v_velocity]
source_id = "{self.input_v_source.text()}"
variable_name = "{self.input_v_var.text()}"

[specification.kernel_parameters]
mindepth = {self.input_mindepth.text()}
driftdepth = {self.input_driftdepth.text()}
maxdepth = {self.input_maxdepth.text()}
vertical_speed = {self.input_v_speed.text()}
cycletime = {self.input_cycletime.text()}
drifttime = {self.input_drifttime.text()}
Kh_zonal = {self.input_kh_zonal.text()}
Kh_meridional = {self.input_kh_meridional.text()}
dres = {self.input_dres.text()}
"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(toml_content)

            QMessageBox.information(self, "Success", f"TOML specification successfully generated and saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate TOML file:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())