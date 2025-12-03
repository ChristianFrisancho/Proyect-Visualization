# World Map & Line Chart

**Purpose:** To provide a high-level, geographic overview of electric vehicle adoption and charging infrastructure over time.

This visualization combines a global choropleth map with an interactive line chart to show where the EV transition is happening and how each country's trajectory has evolved.

![World Map Demo](map_chart.png)

---

### Components and Features

1.  **Interactive World Map:**
    -   Each country is colored based on the value of the selected metric for the year shown on the time slider.
    -   **Hover:** Hovering over a country displays its name and the precise metric value.
    -   **Click:** Clicking a country pins it to the line chart below, allowing you to compare its historical evolution against other selected countries.

2.  **Historical Line Chart:**
    -   Displays the trend of the selected metric across all available years for the countries you have selected on the map.
    -   This allows you to identify trends, inflection points, and compare growth rates between nations.

3.  **Metric Selector (Dropdown):**
    -   Allows you to change the variable displayed on both the map and the line chart.

---

### Implementation Walkthrough

The `WorldMapLineChart` is built in three main steps: data preparation, widget initialization, and linking interactivity.

#### Step 1: Data Preparation

The primary dataset (`wide`) contains data for each `region` and `mode`. For this map, we need to ensure that when a country is clicked, the data for "Cars" is prioritized for coloring the map. This is achieved by sorting the DataFrame.

```python
# Create a copy to work with
wide_sorted = wide.copy()

# Define the priority for vehicle modes
mode_priority = ["Cars", "Vans", "Buses", "Trucks"]

# Helper function to extract mode from the 'label' column
def extract_mode(label: str):
    return label.split("•", 1).strip() if "•" in str(label) else None

# Create temporary columns for sorting
wide_sorted["_mode"] = wide_sorted["label"].apply(extract_mode)
wide_sorted["_mode_rank"] = wide_sorted["_mode"].apply(
    lambda m: mode_priority.index(m) if m in mode_priority else 999
)

# Sort by region first, then by the mode rank
wide_sorted = wide_sorted.sort_values(by=["region", "_mode_rank"]).reset_index(drop=True)
```

#### Step 2: Widget Initialization
We create a dropdown widget for metric selection and initialize the WorldMapLineChart with the prepared data. The initial metric is set to StockShare.
```Python
import ipywidgets as widgets
from Isea.worldmaplinechart import WorldMapLineChart

# Define the list of metrics for the dropdown
metrics = [
    "StockBEV", "StockFCEV", "StockPHEV",
    "SalesBEV", "SalesFCEV", "SalesPHEV",
    "SalesShare", "StockShare",
    "ChargingStations",
]

metric_dropdown = widgets.Dropdown(
    options=metrics,
    value="StockShare",
    description="Metric:",
    layout=widgets.Layout(width="300px"),
)

# Initialize the main widget
w_world = WorldMapLineChart(
    df=wide_sorted,
    metric=metric_dropdown.value,
    region_col="region",
    label_col="label",
    id_col="id",
    title="World EV Map",
    subtitle="Hover, click, and compare countries over time.",
)
```

#### Step 3: Linking Interactivity
An observer function is created to link the dropdown widget to the map. When the user selects a new metric from the dropdown, this function calls set_metric() to update the visualization.
```Python
# Callback function to handle dropdown changes
def on_metric_change(change):
    new_metric = change["new"]
    w_world.set_metric(new_metric)

# Attach the observer to the dropdown
metric_dropdown.observe(on_metric_change, names="value")
```

#### Step 4: Display the Visualization
Finally, we display the dropdown and the map widget together in a vertical box layout.
``` Python
# Display both widgets
widgets.VBox([metric_dropdown, w_world])
```
---

### Available Metrics

-   **StockBEV / PHEV / FCEV:** The absolute number of Battery Electric, Plug-in Hybrid, or Fuel Cell Electric Vehicles on the road. Useful for understanding market size.
-   **SalesBEV / PHEV / FCEV:** The absolute number of EVs sold in a given year. Measures the current market pulse.
-   **StockShare:** The percentage of a country's total vehicle fleet that is electric. This measures market **penetration**.
-   **SalesShare:** The percentage of new vehicle sales in a year that are electric. This measures the **speed of the transition**.
-   **ChargingStations:** The total number of public charging points (both fast and slow). This measures infrastructure adequacy.

---

### Analytical Questions This View Can Anwser

-   Which geographic regions are the clear leaders in EV adoption?
-   How did a country's adoption trajectory change after a specific year?
-   Which countries are investing most heavily in charging infrastructure relative to their size?