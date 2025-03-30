Instalar Unity editor version 6000.0.32f1 con Windows Build Support: unityhub://6000.0.32f1/b2e806cf271c

Ejecutar ./setup_env.bat para instalar todas las dependencias
Luego activar entorno virtual venv/Scripts/activate
Ejecutar main.py


Build app:
pyinstaller --name SimulationManager --onefile --windowed --icon=icono.ico --add-data ".env;." --add-data "icono.ico;." --add-data "img;img" --add-data "Responses;Responses" --add-data "Scripts;Scripts" --add-data "Simulations;Simulations" --add-data "Template;Template" main.py