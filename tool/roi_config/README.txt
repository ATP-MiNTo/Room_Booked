PC ROI Configuration Directory
==============================

This directory stores polygon definitions for PC/workstation areas.

Files are created by running:
    python tool\roi_pc_setup.py

Location: tool/roi_config/

Format: {CameraName}_roi.csv
Example files:
    - Front_right_roi.csv
    - Front_left_roi.csv
    - Back_left_roi.csv
    - Back_right_roi.csv

CSV Structure:
    pc_name,points_json
    PC1,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
    PC2,"[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"

These files are automatically loaded by detection scripts when ENABLE_PC_ROI = True.
