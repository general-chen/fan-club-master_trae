I will add a custom fan icon to the software by following these steps:

1.  **Create Resource Directory**:
    -   Create a new directory `master/resources/icons` to store the icon files.

2.  **Generate Icon Files**:
    -   Write and execute a Python script using `PIL` (Pillow) to generate a 64x64 pixel fan graphic.
    -   Save the graphic as `fan_icon.png` and `fan_icon.ico` in the `master/resources/icons` directory.

3.  **Update Configuration**:
    -   Modify `master/fc/frontend/gui/widgets/base.py` to load the new icons.
    -   Implement logic to detect the operating system and apply the appropriate icon format:
        -   Use `iconbitmap` with `.ico` for Windows (Taskbar, Desktop).
        -   Use `iconphoto` with `.png` for the window title bar and other OS support.
    -   Maintain the existing embedded icon as a fallback.

4.  **Verification**:
    -   Launch the application to verify that the icon appears correctly in the window title bar and taskbar.
