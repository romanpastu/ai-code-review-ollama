#!/bin/bash

# Script to compile 'git_diff_analyzer.py' into an executable and move it to /usr/local/bin

# Variables
SCRIPT_NAME="script.py"
EXECUTABLE_NAME="review"
DESTINATION="/usr/local/bin"

# Check if pyinstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Step 1: Compile the Python script into an executable
echo "Compiling the script with PyInstaller..."
pyinstaller --onefile --name "$EXECUTABLE_NAME" "$SCRIPT_NAME"

# Step 2: Check if the compilation succeeded
if [ ! -f "dist/$EXECUTABLE_NAME" ]; then
    echo "Compilation failed. Please check for errors."
    exit 1
fi

# Step 3: Move the new executable to the destination directory
echo "Moving the new executable to $DESTINATION..."
sudo mv "dist/$EXECUTABLE_NAME" "$DESTINATION"

# Step 4: Clean up build artifacts
echo "Cleaning up build artifacts..."
rm -rf build dist "$EXECUTABLE_NAME.spec"

# Step 5: Verify the executable works
echo "Verifying the new executable..."
if command -v "$EXECUTABLE_NAME" &> /dev/null; then
    echo "✅ The '$EXECUTABLE_NAME' command is now updated and available system-wide!"
else
    echo "❌ Something went wrong. The executable is not found in PATH."
fi
