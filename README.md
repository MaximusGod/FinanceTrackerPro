An open-source and secure desktop application designed to manage personal and family budgets, with all your data stored locally on your device.

-- How to Download and Run the Application

Method 1: Download the Executable Application (Recommended for Users)
No Python installation or terminal commands required:

Go to the Releases section of this GitHub repository.

Download the appropriate file for your operating system:

Windows: FinanceTracker-Windows.exe *

Linux: FinanceTracker-Linux

macOS: FinanceTracker-macOS

Method 2: Run from Source Code (For Developers)

If you downloaded the ZIP source file or cloned the repository using git clone:

On Windows:

Double-click the Avvia_Windows.bat file. It will automatically install the dependencies within a virtual environment and launch the app.

On Linux / macOS:

Open a terminal in the project directory and run:

Bash
chmod +x avvia_linux.sh
./avvia_linux.sh
Or manually:

Bash
# 1. Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
If you would like to build the executable manually using PyInstaller:

Bash
./build_local.sh
The generated binary will be available in the dist/ directory.

Contributions & Feedback
Contributions, suggestions, and code improvements are highly welcome. If you encounter any bugs, have ideas for new features, or wish to optimize the codebase, please feel free to open an issue or submit a pull request.