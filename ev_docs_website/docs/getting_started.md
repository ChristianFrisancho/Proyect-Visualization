# Quick Start Guide

There are two ways to experience this project. For full interactivity, we strongly recommend running the notebook locally.

---

## Option 1: Running the Notebook Locally (Recommended)

This method gives you the full interactive experience, allowing you to use all the custom widgets and run the ML analysis panel on your own selections.

#### Prerequisites
-   Python 3.8+
-   `pip` and `git` installed on your system.

#### Step 1: Clone the Repository
Open your terminal and clone this project's repository to your local machine.
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

#### Step 2: Set Up a Virtual Environment
It is best practice to create a dedicated environment for the project's dependencies.

```bash
# Create the virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (macOS/Linux)
source venv/bin/activate
```

#### Step 3: Install the Required Libraries
The project depends on several Python libraries, including the custom isea-vis package. Install them all with a single command.

```bash
pip install pandas ipywidgets scikit-learn matplotlib seaborn isea-vis
```

> **Note:** If you have a `requirements.txt` file, you can simply run `pip install -r requirements.txt`

#### Step 4: Launch Jupyter and Run the Notebook
You're all set! Start Jupyter and open the main notebook file.

```bash
jupyter notebook P6_deliverable_final.ipynb
```

Once the notebook is open, you can run the cells to generate the visualizations and interact with them.

---

## Option 2: Viewing a Non-Interactive Version Online

If you just want to see the notebook's content and the pre-rendered outputs without running the code yourself, you can use NBViewer.

> **Please note:** The interactive widgets (maps, scatter plots, and analysis panel) will not be functional in this mode. They will appear as static images or empty outputs.

#### How to View:
Simply click the link below to open a rendered version of the notebook directly from the GitHub repository:

[View on NBViewer](https://nbviewer.org/github/YOUR_USERNAME/YOUR_REPOSITORY/blob/main/P6_deliverable_final.ipynb)

*(Remember to replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your actual GitHub details.)*