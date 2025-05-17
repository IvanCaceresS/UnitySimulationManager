# BUILD FOR WINDOWS
- Python 3.9.11 is required  -> https://www.python.org/downloads/release/python-3911/
- Install Unity editor version 6000.0.32f1 with Windows Build Support: unityhub://6000.0.32f1/b2e806cf271c
- Navigate to ./app
- Run ./Windows_build.ps1 to build the app
- The SimulationManager.exe can be found in the ./Windows_dist folder

# BUILD FOR MAC
- Python 3.9.11 is required  -> https://www.python.org/downloads/release/python-3911/
- Install Unity editor version 6000.0.32f1 with Mac Build Support: unityhub://6000.0.32f1/b2e806cf271c
- Navigate to ./app
- chmod +x ./Mac_build.sh
- Run ./Mac_build.sh to build the app
- The SimulationManager.app can be found in the ./Mac_dist folder
- The SimulationManagerLauncher Alias can be found in the ./Mac_dist folder

# RUN - WINDOWS
- Open SimulationManager.exe

# RUN - MAC
- Open SimulationManagerLauncher
- Go to "Privacy & Security" in System Settings and allow "SimulationManagerLauncher" to open, as it may be blocked by default due to being identified as potentially unsafe.
