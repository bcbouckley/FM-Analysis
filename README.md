# FM Moneyball Analysis App

A simple Streamlit application that runs in your web browser and lets you analyse Football Manager player data without needing any coding knowledge.

---

## What this app does

This tool allows you to:

* Import player data exported from Football Manager
* Analyse and filter players using Moneyball-style metrics
* Explore squad-building insights in an interactive interface

No coding experience is required once the setup is complete.

---

## What you need before using it

### 1. Football Manager 2026

You must be able to export player data from Football Manager.

Helpful guides:

* https://youtu.be/NugiVa5xpIY
* https://www.fmscout.com/a-fm26-player-csv-export.html

---

### 2. Custom export view (important)

You must use the included:

**`moneyball.fmf`**

This file ensures the correct data columns are exported.

Without it, the app may not work correctly.

---

### 3. Install the app (one-time setup)

You will need:

* Python installed (version 3.11 or newer recommended)
* GitHub Desktop (recommended for easiest setup)

---

## How to install (easy method)

### Step 1 — Download the project

1. Open GitHub Desktop
2. Click **File → Clone Repository**
3. Select this repository
4. Click **Clone**

---

### Step 2 — Install requirements

Open the project folder and install dependencies:

```bash id="kq9m2a"
pip install -r requirements.txt
```

*(This installs everything the app needs automatically.)*

---

### Step 3 — Run the app

Start the application with:

```bash id="v1x8pl"
streamlit run moneyball.py
```

A browser window will open automatically.

If not, go to:

```
http://localhost:8501
```

---

## How to use

1. Load the `moneyball.fmf` view in Football Manager (make sure to untick the "exclude players from my club" in the edit search box)
2. Export your player data as a CSV ()
3. Open the app in your browser
4. Upload the CSV file
5. Explore and analyse your players

---

## Important notes

* The app expects the exact column structure from `moneyball.fmf`
* Using a different export view may break the analysis
* Very large datasets may take a few seconds to load

---

## Troubleshooting

If something doesn’t work:

* Make sure you're using the correct export view
* Check that your CSV file opens correctly in Excel first
* Reinstall dependencies using `pip install -r requirements.txt`

---

## Purpose

This project is designed to make Football Manager data analysis accessible to non-technical users through a simple browser-based interface.
