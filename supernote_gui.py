import sys
import os
import glob
import supernotelib
from supernotelib.converter import ImageConverter, SvgConverter, PdfConverter
import supernotelib.color as sn_color

try:
    import scour.scour as scour_mod
except ImportError:
    scour_mod = None

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QGridLayout, 
                             QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class ConversionWorker(QThread):
    progress_sig = pyqtSignal(int)
    status_sig = pyqtSignal(str)
    error_sig = pyqtSignal(str, str)
    warning_sig = pyqtSignal(str, str)
    success_sig = pyqtSignal(str, str)
    finished_sig = pyqtSignal()

    def __init__(self, in_file, out_file, fmt, check_all, page_str, check_optimize, custom_palette):
        super().__init__()
        self.in_file = in_file
        self.out_file = out_file
        self.fmt = fmt
        self.check_all = check_all
        self.page_str = page_str
        self.check_optimize = check_optimize
        self.custom_palette = custom_palette

    def run(self):
        try:
            self.status_sig.emit("Reading Supernote file...")
            self.progress_sig.emit(5)  # Immediate visual feedback
            
            with open(self.in_file, 'rb') as f:
                notebook = supernotelib.load(f)
                self.progress_sig.emit(10) # File fully loaded
                
                try:
                    total_pages = notebook.get_total_pages()
                except AttributeError:
                    total_pages = len(notebook.pages) if hasattr(notebook, 'pages') else 1
                
                if self.check_all:
                    pages_to_convert = list(range(total_pages))
                else:
                    parsed_pages = set()
                    if not self.page_str.strip():
                        self.error_sig.emit("Error", "Please enter specific pages to convert, or check 'Convert All Pages'.")
                        return

                    for part in self.page_str.split(','):
                        part = part.strip()
                        if not part: continue
                        
                        if '-' in part:
                            try:
                                start, end = map(int, part.split('-'))
                                parsed_pages.update(range(start, end + 1))
                            except ValueError:
                                self.error_sig.emit("Error", f"Invalid page range format: '{part}'")
                                return
                        else:
                            try:
                                parsed_pages.add(int(part))
                            except ValueError:
                                self.error_sig.emit("Error", f"Invalid page number: '{part}'")
                                return
                    
                    pages_to_convert = [p - 1 for p in sorted(parsed_pages) if 1 <= p <= total_pages]
                    
                    if not pages_to_convert:
                        self.error_sig.emit("Error", f"None of the selected pages are valid. This document has {total_pages} page(s).")
                        return

                generated_files = []
                base_out, _ = os.path.splitext(self.out_file)
                is_optimizing = (self.fmt == "svg" and self.check_optimize)
                
                # Setup proper progress math based on what stages we are doing
                start_prog = 10
                conv_range = 40 if is_optimizing else 90
                num_pages = len(pages_to_convert)
                
                if self.fmt == "pdf":
                    imgs = []
                    converter = ImageConverter(notebook, palette=self.custom_palette)
                    for i, p in enumerate(pages_to_convert):
                        self.status_sig.emit(f"Converting page {i+1} of {num_pages} to PDF...")
                        # Jump to roughly the start of this page's chunk
                        self.progress_sig.emit(start_prog + int(((i + 0.2) / num_pages) * conv_range))
                        
                        img = converter.convert(p)
                        imgs.append(img.convert('RGB'))
                        
                        # Fill the rest of this page's chunk
                        self.progress_sig.emit(start_prog + int(((i + 0.8) / num_pages) * conv_range))
                    
                    if imgs:
                        self.status_sig.emit("Saving PDF file...")
                        imgs[0].save(self.out_file, save_all=True, append_images=imgs[1:])
                        generated_files.append(self.out_file)
                        self.progress_sig.emit(start_prog + conv_range)
                        
                elif self.fmt == "png":
                    converter = ImageConverter(notebook, palette=self.custom_palette)
                    for i, p in enumerate(pages_to_convert):
                        self.status_sig.emit(f"Converting page {i+1} of {num_pages} to PNG...")
                        self.progress_sig.emit(start_prog + int(((i + 0.5) / num_pages) * conv_range))
                        
                        img = converter.convert(p)
                        out_name = self.out_file if len(pages_to_convert) == 1 else f"{base_out}_{p}.png"
                        img.save(out_name)
                        generated_files.append(out_name)
                        
                        self.progress_sig.emit(start_prog + int(((i + 1) / num_pages) * conv_range))
                        
                elif self.fmt == "svg":
                    converter = SvgConverter(notebook, palette=self.custom_palette)
                    for i, p in enumerate(pages_to_convert):
                        self.status_sig.emit(f"Converting page {i+1} of {num_pages} to SVG...")
                        self.progress_sig.emit(start_prog + int(((i + 0.5) / num_pages) * conv_range))
                        
                        svg_data = converter.convert(p)
                        out_name = self.out_file if len(pages_to_convert) == 1 else f"{base_out}_{p}.svg"
                        with open(out_name, 'w', encoding='utf-8') as svg_out:
                            svg_out.write(svg_data.decode('utf-8') if isinstance(svg_data, bytes) else str(svg_data))
                        generated_files.append(out_name)
                        
                        self.progress_sig.emit(start_prog + int(((i + 1) / num_pages) * conv_range))
                        
            generated_files = [f for f in generated_files if os.path.exists(f)]
            
            if not generated_files:
                self.warning_sig.emit("Warning", "Conversion completed, but could not locate the output files.")
                return

            if is_optimizing:
                self.status_sig.emit(f"Optimizing {len(generated_files)} SVG(s)...")
                if scour_mod is not None:
                    opt_start = 50
                    opt_range = 50
                    total_files = len(generated_files)
                    
                    for i, target_file in enumerate(generated_files):
                        self.status_sig.emit(f"Optimizing SVG {i+1} of {total_files}...")
                        self.progress_sig.emit(opt_start + int(((i + 0.5) / total_files) * opt_range))
                        
                        temp_out = target_file + ".tmp"
                        old_argv = sys.argv
                        sys.argv = [
                            "scour", "-i", target_file, "-o", temp_out,
                            "--enable-viewboxing", "--enable-id-stripping", "--shorten-ids",
                            "--indent=none", "--remove-metadata", "--strip-xml-prolog"
                        ]
                        
                        try:
                            scour_mod.run()
                        except SystemExit as e:
                            if e.code is not None and e.code != 0:
                                print(f"Scour optimization issue on {target_file}, code {e.code}")
                        finally:
                            sys.argv = old_argv
                        
                        if os.path.exists(temp_out):
                            os.replace(temp_out, target_file)
                            
                        self.progress_sig.emit(opt_start + int(((i + 1) / total_files) * opt_range))
                    
                    self.progress_sig.emit(100)
                    self.status_sig.emit("Finished!")
                    self.success_sig.emit("Success", f"Successfully converted and OPTIMIZED {len(generated_files)} file(s)!")
                else:
                    self.progress_sig.emit(100)
                    self.status_sig.emit("Finished (Optimization Skipped).")
                    self.warning_sig.emit("Optimization Skipped", f"Converted {len(generated_files)} file(s), but the Scour optimization engine was not bundled.")
            else:
                self.progress_sig.emit(100)
                self.status_sig.emit("Finished!")
                self.success_sig.emit("Success", f"Successfully converted {len(generated_files)} file(s)!")
                
        except Exception as e:
            self.error_sig.emit("Process Failed", f"An error occurred during processing:\n{str(e)}")
        finally:
            self.finished_sig.emit()

class SupernoteConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supernote to SVG/PDF Converter")
        
        # Widened and heightened slightly to accommodate the progress bar and new options
        self.resize(700, 340)
        self.setMinimumSize(650, 310)

        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        # Forces the middle column (the text boxes) to stretch and fill space, preventing collapse
        grid.setColumnStretch(1, 1)

        # --- Input Row ---
        lbl_input = QLabel("Input (.note):")
        lbl_input.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(lbl_input, 0, 0)
        
        self.input_edit = QLineEdit()
        grid.addWidget(self.input_edit, 0, 1)
        
        self.btn_browse_in = QPushButton("Browse...")
        self.btn_browse_in.clicked.connect(self.browse_input)
        grid.addWidget(self.btn_browse_in, 0, 2)

        # --- Output Row ---
        lbl_output = QLabel("Output File:")
        lbl_output.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(lbl_output, 1, 0)
        
        self.output_edit = QLineEdit()
        grid.addWidget(self.output_edit, 1, 1)
        
        self.btn_browse_out = QPushButton("Browse...")
        self.btn_browse_out.clicked.connect(self.browse_output)
        grid.addWidget(self.btn_browse_out, 1, 2)

        main_layout.addLayout(grid)

        # --- Options Row 1: Formats & Pages ---
        opt_layout = QHBoxLayout()
        opt_layout.setContentsMargins(0, 10, 0, 5)
        
        opt_layout.addWidget(QLabel("Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["svg", "pdf", "png"])
        self.format_combo.currentTextChanged.connect(self.update_format_options)
        opt_layout.addWidget(self.format_combo)

        self.check_all = QCheckBox("Convert All Pages")
        self.check_all.setChecked(True)
        opt_layout.addWidget(self.check_all)

        # Custom Page Selection Input
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("e.g. 1-3, 5")
        self.page_input.setFixedWidth(100)
        self.page_input.setEnabled(False) 
        
        self.check_all.toggled.connect(lambda checked: self.page_input.setDisabled(checked))
        opt_layout.addWidget(self.page_input)
        
        opt_layout.addSpacing(15)
        
        self.check_optimize = QCheckBox("Optimize SVG Size")
        self.check_optimize.setChecked(True)
        opt_layout.addWidget(self.check_optimize)
        
        opt_layout.addStretch()
        main_layout.addLayout(opt_layout)

        # --- Options Row 2: Colorization ---
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 10)
        
        self.check_colorize = QCheckBox("Colourise Ink:")
        self.check_colorize.setToolTip("Override the default black/gray ink.")
        self.check_colorize.setChecked(False)
        
        self.color_preset_combo = QComboBox()
        self.color_preset_combo.addItems(["Red", "Pen Blue", "Green", "Dark Mode (White Ink)", "Custom"])
        self.color_preset_combo.setEnabled(False)
        self.color_preset_combo.currentTextChanged.connect(self.update_color_preset)
        
        self.color_input = QLineEdit()
        self.color_input.setText("#DC143C,#9d9d9d,#c9c9c9,#fefefe") # Default to Red preset
        self.color_input.setPlaceholderText("#black, #darkgray, #gray, #white")
        self.color_input.setEnabled(False)
        
        # Toggle enabled state for both dropdown and input
        self.check_colorize.toggled.connect(self.toggle_color_inputs)
        
        color_layout.addWidget(self.check_colorize)
        color_layout.addWidget(self.color_preset_combo)
        color_layout.addWidget(self.color_input)
        
        # Ensure the hex input stretches to fill space
        color_layout.setStretchFactor(self.color_input, 1)
        
        main_layout.addLayout(color_layout)

        # Add stretch to push progress/button down and inputs up, fixing UI spacing!
        main_layout.addStretch(1)

        # --- Progress Row ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        main_layout.addWidget(self.progress_bar)

        # --- Action Row ---
        self.btn_convert = QPushButton("Convert File")
        self.btn_convert.setMinimumHeight(40)
        self.btn_convert.setStyleSheet("font-weight: bold;")
        self.btn_convert.clicked.connect(self.run_conversion)
        main_layout.addWidget(self.btn_convert)

        self.setLayout(main_layout)

    def browse_input(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Supernote File", "", "Supernote files (*.note)")
        if filepath:
            self.input_edit.setText(filepath)
            
            base, _ = os.path.splitext(filepath)
            ext = self.format_combo.currentText()
            self.output_edit.setText(f"{base}.{ext}")

    def browse_output(self):
        ext = self.format_combo.currentText()
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save File As", "", f"{ext.upper()} files (*.{ext})")
        if filepath:
            self.output_edit.setText(filepath)

    def update_format_options(self, new_ext):
        current_out = self.output_edit.text()
        if current_out:
            base, _ = os.path.splitext(current_out)
            self.output_edit.setText(f"{base}.{new_ext}")
            
        self.check_optimize.setEnabled(new_ext == "svg")

    def toggle_color_inputs(self, checked):
        self.color_preset_combo.setDisabled(not checked)
        self.color_input.setDisabled(not checked)

    def update_color_preset(self, preset):
        if preset == "Red":
            self.color_input.setText("#DC143C,#9d9d9d,#c9c9c9,#fefefe")
        elif preset == "Pen Blue":
            self.color_input.setText("#0000CD,#9d9d9d,#c9c9c9,#fefefe")
        elif preset == "Green":
            self.color_input.setText("#228B22,#9d9d9d,#c9c9c9,#fefefe")
        elif preset == "Dark Mode (White Ink)":
            # Inverts the main ink to white and flips the grays, making the background black/transparent
            self.color_input.setText("#fefefe,#c9c9c9,#9d9d9d,#000000")
        elif preset == "Custom":
            # Leave the text as-is to allow user editing
            pass

    def run_conversion(self):
        # Immediately disable the button to prevent accidental double-clicks queueing multiple conversions
        self.btn_convert.setEnabled(False)

        in_file = self.input_edit.text()
        out_file = self.output_edit.text()
        fmt = self.format_combo.currentText()

        if not in_file or not out_file:
            QMessageBox.critical(self, "Error", "Please select both an input and an output file.")
            self.btn_convert.setEnabled(True)
            return

        # --- Overwrite Protection Check ---
        base_out, _ = os.path.splitext(out_file)
        existing_files = []
        
        # Check main targeted file
        if os.path.exists(out_file):
            existing_files.append(out_file)
            
        # Check potential auto-generated paginated files (e.g. filename_0.png)
        if fmt in ["png", "svg"]:
            existing_files.extend([f for f in glob.glob(f"{base_out}_*.{fmt}") if os.path.exists(f)])
            
        # Remove duplicates
        existing_files = list(set(existing_files))
        
        if existing_files:
            reply = QMessageBox.question(
                self, 
                'Overwrite Files?',
                f"Warning: One or more output files already exist and will be overwritten.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            # Catch ANY dismissal (No, clicking the 'X', pressing Escape)
            if reply != QMessageBox.StandardButton.Yes:
                self.btn_convert.setEnabled(True)
                return

        # --- Parse Custom Colors ---
        custom_palette = None
        if self.check_colorize.isChecked():
            color_str = self.color_input.text().strip()
            if color_str:
                try:
                    parsed_colors = []
                    for c in color_str.split(','):
                        c = c.strip().lstrip('#')
                        if len(c) == 6:   # Standard RGB
                            # The engine expects a 24-bit integer, not a tuple!
                            parsed_colors.append(int(c, 16))
                        elif len(c) == 8: # Handle RGBA by safely stripping alpha for engine compatibility
                            parsed_colors.append(int(c[:6], 16))
                        else:
                            raise ValueError(f"Invalid hex string: #{c}")
                    
                    # Create the native engine palette
                    custom_palette = sn_color.ColorPalette(sn_color.MODE_RGB, parsed_colors)
                except Exception as e:
                    QMessageBox.critical(self, "Color Error", f"Failed to parse custom colors.\n\nPlease use exactly 4 hex codes separated by commas.\nExample: #ff0000,#9d9d9d,#c9c9c9,#fefefe\n\nDetails: {e}")
                    self.btn_convert.setEnabled(True)
                    return

        # --- Native Threaded Conversion ---
        self.btn_convert.setText("Converting...")
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting conversion...")
        
        # Pass the heavy lifting to a background thread to prevent the Mac Beachball
        self.worker = ConversionWorker(
            in_file, out_file, fmt, 
            self.check_all.isChecked(), self.page_input.text(), 
            self.check_optimize.isChecked(), custom_palette
        )
        
        # Connect the thread's signals back to the main UI
        self.worker.progress_sig.connect(self.progress_bar.setValue)
        self.worker.status_sig.connect(self.status_label.setText)
        self.worker.error_sig.connect(self.show_error)
        self.worker.warning_sig.connect(self.show_warning)
        self.worker.success_sig.connect(self.show_success)
        self.worker.finished_sig.connect(self.conversion_finished)
        self.worker.start()

    def show_error(self, title, msg):
        QMessageBox.critical(self, title, msg)

    def show_warning(self, title, msg):
        QMessageBox.warning(self, title, msg)

    def show_success(self, title, msg):
        QMessageBox.information(self, title, msg)

    def conversion_finished(self):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("Convert File")
        # Reset UI state after popup is dismissed
        self.progress_bar.setValue(0)
        self.status_label.setText("")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SupernoteConverterApp()
    window.show()
    sys.exit(app.exec())