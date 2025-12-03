# Diagnostic Scatter Plot

**Purpose:** To perform a detailed diagnostic analysis to compare metrics, identify relationships, and analyze subgroups of regions and transport modes.

This interactive scatter plot is the central tool for deep-dive analysis. It provides complete flexibility to explore the relationships between different variables and how those relationships evolve over time.

![Scatter Plot Demo](scatter.gif)

---

### Components and Features

1.  **Dynamic Axes (X/Y):**
    -   You can select any of the available metrics for the X and Y axes from the control panel, enabling endless comparisons.

2.  **Time Slider:**
    -   Filters the data to show only the selected year. Animating the slider reveals the evolution of regions over time.

3.  **Brushing and Linked View:**
    -   Click and drag to select a group of points. A second, linked scatter plot will appear below, showing only your selected points. This is ideal for focused analysis without the noise of other data.

4.  **Legend Filtering:**
    -   Click on the labels in the legend (`Cars`, `Buses`, `Vans`, `Trucks`) to toggle the visibility of different transport modes, allowing you to isolate specific patterns.

5.  **Analytical Overlays (Buttons):**
    -   **`x=y`:** Draws a diagonal line that is essential for ratio and acceleration analysis (see tutorials).
    -   **`0-100`:** Normalizes the axes to a percentage scale, which is useful for comparing "Share" metrics.
    -   **`Lock Axes`:** Locks the scale of the axes, allowing for a consistent visual comparison as you move the time slider.


---

### Implementation Walkthrough

This visualization consists of two `ScatterBrush` widgets: a primary chart for exploration and a secondary, linked chart that mirrors the user's selection.

#### Step 1: Main Scatter Plot Initialization

First, we initialize the main `ScatterBrush` widget. We provide it with the full `wide` DataFrame and set default values for the X and Y axes (`StockShare` and `SalesShare`).

```python
from Isea.scatter import ScatterBrush

# The 'wide' DataFrame is already prepared from the first cell
# 'xyVars', 'yearMin', 'yearMax' are also pre-calculated

w = ScatterBrush(
    wide,
    x="StockShare",   # Default X-axis
    y="SalesShare",   # Default Y-axis
    key="id",
    label="label",
    color="mode",
    legend=True,
    xyVars=xyVars,
    yearMin=yearMin,
    yearMax=yearMax,
    width=1080,
    height=520,
)

# To display it, you simply call the widget variable
w
```

#### Step 2: Linked Scatter Plot and Sync Logic
Next, we create a second, initially empty ScatterBrush widget (w_link). We then define a _sync function that will be responsible for updating this second chart based on interactions with the first one.
``` Python
# Create an empty second widget with the same configuration
w_link = ScatterBrush(
    wide.iloc[0:0].to_dict("records"), # Initially empty data
    x="StockShare", y="SalesShare",
    key="id", label="label", color="mode",
    # ... other config options match the primary widget
)

# This function contains the logic to synchronize the two charts
def _sync(*_):
    # 1. Get the current axes from the main widget
    opts = getattr(w, "options", {}) or {}
    x, y = opts.get("x"), opts.get("y")

    # 2. Get the current selection (the "brushed" points)
    sel = w.selection if isinstance(w.selection, dict) else {}
    keys = sel.get("keys", []) or []
    
    # 3. Filter the main DataFrame to get the selected data
    sub = wide[wide["id"].isin(keys)] if keys else wide.iloc[0:0]

    # 4. Push the new data and axis settings to the linked widget
    w_link.data = sub.to_dict("records")
    w_link.options = {**(w_link.options or {}), "x": x, "y": y}

display(w_link)

```

#### Step 3: Linking Interactivity with Observers
To make the synchronization happen automatically, we attach the _sync function to the selection and options properties of the main widget (w). Now, whenever the user brushes points or changes an axis, _sync is called.
``` Python
# React to changes in the selection (brushing)
w.observe(lambda ch: _sync(), names="selection")

# React to changes in the options (like changing an axis)
w.observe(lambda ch: _sync(), names="options")

# Run sync once initially to ensure the linked chart is correctly configured
_sync()
```

---

### Analytical Questions This View Can Answer

-   Is there a linear relationship between the number of chargers and BEV sales?
-   Which countries are accelerating their transition the fastest (Sales Share > Stock Share)?
-   How do the adoption profiles of buses versus cars compare in Europe?

For detailed examples of how to use this tool, please see our tutorials.