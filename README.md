# OpenMobile_OS
This is just the files for my open source rpi/sbc os made for 3.5 inch touchscreens. This is still in development.


# This is still in development, there is no apps preinstalled. No point setting it up now.

Currently to run it:
1. Download the files
2. Install raspbian os lite
3. Install Python and pygame
4. Extract the files to the folder where you want the files stored
5. If your using a touch (like the 3.5 this was origionally designed for), install the firmware
6. A command to run on boot to load the UI in the framebuffer. The new boot file is bootloader.py
7. Follow the set up prompt

# New Version Release: B.0.3
- New apps added:
  - Help app
  - JEX web browser
- Appstore updated:
  Refreshed UI, search functionality, fixed bug where it can freeze randomly
- Settings app Refreshed
  More functionality added, refreshed design, reboot and reset functions will be added again next update
- File Manager upgrade:
  Complete new app, bugs fixed, new UI, new previewer
  The old file manager can still be used, it is now named legacy_files
- New notification types added:
  rdialogue - The dialogue but it can ring
  ring - The message but it can ring
- Folder system added to UI
  You can now create and edit folders
- Legacy UI updates
  For low end devices, the legacy UI can now be used, it has now been updated so it can open apps. No icons or notification systems or folders will be implemented into this old UI
- New bootloader:
  This will run the main.py file, if any errors are detected, it will fix this and reinstall a local backup of the software. All data will be lost though and system may be downgraded into an older version of the software


# New version release: B.0.1

This includes a new appstore, notification system which allows for showing bannar notifications, dialogue and messages in the desktop, finally a new personal assistant named kit.

More documentation will be released on a later date.