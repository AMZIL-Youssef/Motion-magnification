# Motion Magnification

## Description
This project implements Eulerian Video Magnification techniques to enhance subtle motions in videos. It provides a user-friendly GUI for loading videos, configuring parameters, and processing the video to produce magnified output. The application utilizes Laplacian pyramids for efficient processing and reconstruction of video frames.

---

## Installation Instructions
1. Clone the repository:
   ```
   git clone https://github.com/AMZIL-Youssef/Motion-magnification.git
   ```
2. Navigate to the project directory:
   ```
   cd motion-magnification
   ```
3. Install the required dependencies

---

## Usage Guidelines
1. Run the application:
   ```
   python app/main.py
   ```
2. Use the GUI to select a video file and configure the parameters for Eulerian Video Magnification.
3. Click on "Traiter la Vidéo" to start the processing.
4. The output video will be saved in the `results` directory.

---

## Directory Structure
```
motion-magnification
├── app
│   ├── evm.py          # Core functionality for Eulerian Video Magnification
│   ├── gui.py          # GUI implementation using PySide6
│   ├── main.py         # Entry point for the application
│   └── pyramid_utils.py # Utility functions for image pyramids
├── data                # Directory for input videos 
├── results             # Directory for output videos
└── README.md           # Project documentation
```

---

## Support

For issues or feature requests, please open an issue on the [GitHub repository](https://github.com/AMZIL-Youssef/Motion-magnification).