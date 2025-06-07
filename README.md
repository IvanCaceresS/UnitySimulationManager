# Unity Simulation Manager

This guide provides instructions on how to build and run the Unity Simulation Manager application on both Windows and macOS.

## 1. Prerequisites

Before you begin, ensure you have the following:

* An OpenAI account and API key.
* The necessary fine-tuning data files: `fine-tuning-LLM1_v4.jsonl` and `fine-tuning-LLM2_v2.jsonl`.

## 2. Environment Setup (.env file)

A crucial step for building the application on both Windows and macOS is creating an environment file named `.env`.

1.  **Create the file:** In the `/app` directory of the project, create a new file named `.env`.
2.  **Populate the file:** Add the following content to your `.env` file:

    ```env
    UNITY_EXECUTABLE=
    UNITY_PROJECTS_PATH=
    OPENAI_API_KEY=
    FINE_TUNED_MODEL_NAME=
    2ND_FINE_TUNED_MODEL_NAME=
    ```

3.  **Fill in the required values:** You **must** provide values for the following variables in the `.env` file:
    * `OPENAI_API_KEY`: Your API key obtained from your OpenAI account dashboard.
    * `FINE_TUNED_MODEL_NAME`: The identifier of your first fine-tuned model.
    * `2ND_FINE_TUNED_MODEL_NAME`: The identifier of your second fine-tuned model.

    The `UNITY_EXECUTABLE` and `UNITY_PROJECTS_PATH` variables are likely related to your Unity Engine installation and project locations, respectively. Fill them in if you know the paths, otherwise, the build scripts might handle them or prompt you.

## 3. OpenAI Model Fine-Tuning

To get the `FINE_TUNED_MODEL_NAME` and `2ND_FINE_TUNED_MODEL_NAME`, you need to fine-tune two separate models using your OpenAI account.

### Model 1: `FINE_TUNED_MODEL_NAME`

* **Dataset:** Use the `fine-tuning-LLM1_v4.jsonl` file.
* **Training Parameters:**
    * `EPOCHS`: 10
    * `BATCH_SIZE`: 1
    * `LEARNING_RATE_MULTIPLIER`: 1.8
    * `Seed`: 1875054926
* **Approximate Training Cost:** $0.7854 USD

### Model 2: `2ND_FINE_TUNED_MODEL_NAME`

* **Dataset:** Use the `fine-tuning-LLM2_v2.jsonl` file.
* **Training Parameters:**
    * `EPOCHS`: 4
    * `BATCH_SIZE`: 1
    * `LEARNING_RATE_MULTIPLIER`: 1.8
    * `Seed`: 2066556991
* **Approximate Training Cost:** $0.0903 USD

After initiating the fine-tuning jobs via the OpenAI API or platform, you will receive unique model identifiers for each. Use these identifiers for `FINE_TUNED_MODEL_NAME` and `2ND_FINE_TUNED_MODEL_NAME` in your `.env` file.

## 4. Building and Running the Application

Once your `.env` file is correctly set up with your OpenAI API key and fine-tuned model names, you can proceed to build the application.

### On Windows

1.  **Python Version:** Ensure you have Python version 3.9.11 installed.
2.  **Python in PATH:** Add your Python 3.9.11 installation directory to your system's PATH environment variable.
3.  **Execute Build Script:** Open PowerShell, navigate to the `/app` directory, and run the `Windows_build.ps1` script:
    ```powershell
    .\Windows_build.ps1
    ```
4.  **Run Application:** After a successful build, the application will be located at `./Windows_dist/SimulationManager.exe`. You can run this executable.

### On macOS

1.  **Environment File:** Ensure your `.env` file in the `/app` directory is correctly configured as described in Section 2.
2.  **Execute Build Script:** Open Terminal, navigate to the `/app` directory, and run the `Mac_build.sh` script with `sudo` permissions. The script will handle the installation of the required Python version automatically.
    ```bash
    sudo ./Mac_build.sh
    ```
3.  **Run Application:** After the build process completes, the application bundle will be named `SimulationManager.app`. The executable is located inside this bundle at `SimulationManager.app/Contents/MacOS/SimulationManager`. To run it, navigate to this path in the Terminal and execute it:
    ```bash
    ./SimulationManager.app/Contents/MacOS/SimulationManager
    ```
    Alternatively, you might be able to run it by double-clicking the `SimulationManager.app` bundle in Finder, but running from the terminal as shown above is recommended if you encounter issues or need to see console output.

## Troubleshooting

* **`.env` file not found:** Ensure the `.env` file is in the correct `/app` directory and is named exactly `.env` (not `.env.txt` or similar).
* **API Key Issues:** Double-check that your `OPENAI_API_KEY` is correct and has the necessary permissions for fine-tuning and model usage.
* **Model Name Issues:** Verify that the `FINE_TUNED_MODEL_NAME` and `2ND_FINE_TUNED_MODEL_NAME` exactly match the identifiers provided by OpenAI after successful fine-tuning.
* **Python Path (Windows):** If the `Windows_build.ps1` script cannot find Python, confirm that Python 3.9.11 is correctly installed and its path is included in your system's PATH environment variable. You might need to restart your PowerShell session or your computer after updating the PATH.
* **Permissions (Mac):** The `Mac_build.sh` script requires `sudo` to install dependencies. Ensure you provide your administrator password when prompted.

