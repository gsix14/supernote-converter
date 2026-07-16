import sys
import os
import glob
import supernotelib
from supernotelib.converter import ImageConverter, SvgConverter, PdfConverter

try:
    import scour.scour as scour_mod
except ImportError:
    scour_mod = None

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QCheckBox, QGridLayout, 
                             QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt

class SupernoteConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supernote to SVG/PDF Converter")
        
        # Widened slightly to accommodate the new page selection input
        self.resize(700, 250)
        self.setMinimumSize(650, 220)

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

        # --- Options Row ---
        opt_layout = QHBoxLayout()
        opt_layout.setContentsMargins(0, 10, 0, 10)
        
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
        self.page_input.setEnabled(False) # Disabled by default since check_all is True
        
        # Connect the checkbox toggle to disable/enable the page input
        self.check_all.toggled.connect(lambda checked: self.page_input.setDisabled(checked))
        opt_layout.addWidget(self.page_input)
        
        # Add spacing before the next checkbox
        opt_layout.addSpacing(15)
        
        self.check_optimize = QCheckBox("Optimize SVG Size")
        self.check_optimize.setChecked(True)
        opt_layout.addWidget(self.check_optimize)
        
        opt_layout.addStretch()

        main_layout.addLayout(opt_layout)

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

    def run_conversion(self):
        in_file = self.input_edit.text()
        out_file = self.output_edit.text()
        fmt = self.format_combo.currentText()

        if not in_file or not out_file:
            QMessageBox.critical(self, "Error", "Please select both an input and an output file.")
            return

        try:
            self.btn_convert.setEnabled(False)
            self.btn_convert.setText("Converting...")
            QApplication.processEvents()
            
            # --- Native Programmatic Conversion ---
            with open(in_file, 'rb') as f:
                notebook = supernotelib.load(f)
                
                try:
                    total_pages = notebook.get_total_pages()
                except AttributeError:
                    total_pages = len(notebook.pages) if hasattr(notebook, 'pages') else 1
                
                # --- Page Parsing Logic ---
                if self.check_all.isChecked():
                    pages_to_convert = list(range(total_pages))
                else:
                    page_str = self.page_input.text()
                    parsed_pages = set()
                    
                    if not page_str.strip():
                        QMessageBox.critical(self, "Error", "Please enter specific pages to convert, or check 'Convert All Pages'.")
                        self.btn_convert.setEnabled(True)
                        self.btn_convert.setText("Convert File")
                        return

                    for part in page_str.split(','):
                        part = part.strip()
                        if not part: continue
                        
                        if '-' in part:
                            try:
                                start, end = map(int, part.split('-'))
                                parsed_pages.update(range(start, end + 1))
                            except ValueError:
                                QMessageBox.critical(self, "Error", f"Invalid page range format: '{part}'")
                                self.btn_convert.setEnabled(True)
                                self.btn_convert.setText("Convert File")
                                return
                        else:
                            try:
                                parsed_pages.add(int(part))
                            except ValueError:
                                QMessageBox.critical(self, "Error", f"Invalid page number: '{part}'")
                                self.btn_convert.setEnabled(True)
                                self.btn_convert.setText("Convert File")
                                return
                    
                    # Convert to 0-indexed and filter out pages that are out of bounds
                    pages_to_convert = [p - 1 for p in sorted(parsed_pages) if 1 <= p <= total_pages]
                    
                    if not pages_to_convert:
                        QMessageBox.critical(self, "Error", f"None of the selected pages are valid. This document has {total_pages} page(s).")
                        self.btn_convert.setEnabled(True)
                        self.btn_convert.setText("Convert File")
                        return

                generated_files = []
                base_out, _ = os.path.splitext(out_file)
                
                if fmt == "pdf":
                    # Convert pages to images and compile into a single PDF
                    imgs = []
                    for p in pages_to_convert:
                        img = ImageConverter(notebook).convert(p)
                        imgs.append(img.convert('RGB'))
                    
                    if imgs:
                        imgs[0].save(out_file, save_all=True, append_images=imgs[1:])
                        generated_files.append(out_file)
                        
                elif fmt == "png":
                    for p in pages_to_convert:
                        img = ImageConverter(notebook).convert(p)
                        # Append page number if outputting multiple images
                        out_name = out_file if len(pages_to_convert) == 1 else f"{base_out}_{p}.png"
                        img.save(out_name)
                        generated_files.append(out_name)
                        
                elif fmt == "svg":
                    for p in pages_to_convert:
                        svg_data = SvgConverter(notebook).convert(p)
                        # Append page number if outputting multiple images
                        out_name = out_file if len(pages_to_convert) == 1 else f"{base_out}_{p}.svg"
                        with open(out_name, 'w', encoding='utf-8') as svg_out:
                            # Ensures format compatibility whether the engine returns strings or bytes
                            svg_out.write(svg_data.decode('utf-8') if isinstance(svg_data, bytes) else str(svg_data))
                        generated_files.append(out_name)
                        
            # Verify the files actually generated properly
            generated_files = [f for f in generated_files if os.path.exists(f)]
            
            if not generated_files:
                QMessageBox.warning(self, "Warning", "Conversion completed, but could not locate the output files.")
                return

            # --- In-Process SVG Optimization ---
            if fmt == "svg" and self.check_optimize.isChecked():
                self.btn_convert.setText(f"Optimizing {len(generated_files)} SVG(s)...")
                QApplication.processEvents()
                
                if scour_mod is not None:
                    for target_file in generated_files:
                        temp_out = target_file + ".tmp"
                        
                        # Mock sys.argv for Scour
                        old_argv = sys.argv
                        sys.argv = [
                            "scour",
                            "-i", target_file,
                            "-o", temp_out,
                            "--enable-viewboxing",
                            "--enable-id-stripping",
                            "--shorten-ids",
                            "--indent=none",
                            "--remove-metadata",
                            "--strip-xml-prolog"
                        ]
                        
                        try:
                            scour_mod.run()
                        except SystemExit as e:
                            if e.code is not None and e.code != 0:
                                print(f"Scour optimization issue on {target_file}, code {e.code}")
                        finally:
                            sys.argv = old_argv
                        
                        # If scour succeeded, replace the bloated SVG with the optimized one
                        if os.path.exists(temp_out):
                            os.replace(temp_out, target_file)
                    
                    QMessageBox.information(
                        self, "Success", f"Successfully converted and OPTIMIZED {len(generated_files)} file(s)!"
                    )
                else:
                    QMessageBox.warning(
                        self, "Optimization Skipped", 
                        f"Converted {len(generated_files)} file(s), but the Scour optimization engine was not bundled."
                    )
            else:
                QMessageBox.information(
                    self, "Success", f"Successfully converted {len(generated_files)} file(s)!"
                )
            
        except Exception as e:
            QMessageBox.critical(self, "Process Failed", f"An error occurred during processing:\n{str(e)}")
        finally:
            self.btn_convert.setEnabled(True)
            self.btn_convert.setText("Convert File")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SupernoteConverterApp()
    window.show()
    sys.exit(app.exec())