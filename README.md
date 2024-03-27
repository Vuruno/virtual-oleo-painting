1. Install Blender from [this link](https://www.blender.org/download/) (I suggest Blender 4.0, but any version is fine)
2. Make sure you have installed the last version of [Pyhton](https://www.python.org/downloads/)
3. Run Blender as *Administrator*, open the tal *Scripting* , write in the text editor and run with `Alt+P`
```
import pip
pip.main(['install', 'opencv-python'])
pip.main(['install', 'cvzone'])
pip.main(['install', 'mediapipe'])
```
4. Download the Repository as .zip and extract in a folder
5. In Blender:  
	- Edit
	- Preferences
	- Add-ons
	- Install
	- (your path)/`realistic virtual oleo painting.py`
	- Install
	- Check `DEMO: Realistic Canvas` box`
