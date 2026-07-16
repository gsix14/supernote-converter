# **Supernote Converter GUI**

A self-contained desktop application for converting Ratta Supernote .note files into highly optimized SVGs, multi-page PDFs, and PNGs.

This app provides a user-friendly graphical interface (GUI) that bypasses the command line, making it incredibly easy to back up your handwritten notes, host handwritten blogs, or export your drawings.

## **✨ Features**

* **Lossless Vector Export:** Export your pen strokes as crisp, infinitely scalable SVGs perfectly suited for web design.  
* **Automatic SVG Optimization:** Built-in integration with scour to automatically strip unnecessary metadata and optimize paths, reducing SVG file sizes by over 50% without losing visual quality.  
* **Selective Page Conversion:** Convert an entire notebook at once, or easily specify exactly which pages to export (e.g., 1-3, 5, 8).  
* **Multi-Page PDFs:** Instantly compile your handwritten notes into a standard, easily shareable PDF document. *Note: pdfs exported from the official partner app may be smaller for the same quality.*  
* **Native OS Look & Feel:** Built with PyQt6 to seamlessly blend with your operating system's native window styling.

## **🛠 What it is based on**

This application stands on the shoulders of some fantastic open-source projects. It acts as a graphical wrapper and automation tool for:

* [**supernotelib**](https://github.com/jya-dev/supernote-tool)**:** The core parsing engine that decodes the proprietary .note format.  
* [**Scour**](https://github.com/scour-project/scour)**:** An SVG optimizer/minifier written in Python.  
* [**PyQt6**](https://pypi.org/project/PyQt6/)**:** A comprehensive set of Python bindings for the Qt v6 application framework.

## **🚀 How to Download and Run (Non-Technical Users)**

If you just want to use the app without messing with Python or the terminal, you can download the pre-packaged application or Mac.

1. Go to the [**Releases**](https://github.com/gsix14/supernote-converter/releases) page on this GitHub repository.  
2. Download the latest Supernote Converter.app.zip (for macOS).  
3. Unzip the file and drag **Supernote Converter.app** into your Applications folder.  
4. **macOS Security Note:** Because this app is made by an independent developer, macOS might show an "unidentified developer" warning the first time you open it.  
   * To bypass this, **Right-click** (or Control-click) the app icon and select **Open** from the menu. Click **Open** again on the popup. You only have to do this once\!

## **💻 How to Build from Source (For Developers)**

If you want to read the code, run it directly from your terminal, or package it for a different operating system (like Windows or Linux), follow these steps:

### **Prerequisites**

Make sure you have Python 3.8+ installed on your system.

### **1\. Clone the repository**

git clone \[https://github.com/gsix14/supernote-converter.git](https://github.com/gsix14/supernote-converter.git)  
cd supernote-converter

### **2\. Install the required dependencies**

The app requires supernotelib, scour, and PyQt6 to run, and pyinstaller if you wish to package it.

pip install supernotelib scour PyQt6 pyinstaller

### **3\. Run the app directly**

You can test the app without packaging it by running:

python supernote\_gui.py

### **4\. Package the app into a standalone executable**

To bundle the Python engine, the math libraries, and the GUI into a single, double-clickable application, use PyInstaller.

Run the following command in your terminal:

python \-m PyInstaller \--windowed \--noconsole \--name "Supernote Converter" supernote\_gui.py

*Once finished, your self-contained application will be located inside the newly generated dist folder.*

## **📝 License**

This project is open-source. Please refer to the respective licenses of supernotelib and scour regarding the core conversion engines.
