# Heatmap

**Purpose:** To visualize the correlation or relationship intensity between multiple variables in a matrix format.

This visualization displays a grid of colored cells where the color intensity represents the value at each intersection, making it perfect for correlation matrices or cross-tabulated data.

![Heatmap Demo](matrix.gif)

---

### Components and Features

1.  **Color-Coded Matrix:**
    -   Each cell represents the intersection of a row and column variable.
    -   Color intensity indicates the value magnitude, with support for diverging colormaps (e.g., `coolwarm` for correlations).

2.  **Interactive Tooltips:**
    -   **Hover:** Displays the exact row, column, and value for any cell.
    -   Cells are highlighted on hover for easy identification.

3.  **Value Labels:**
    -   When cells are large enough, numeric values are displayed directly on the heatmap for quick reading.

4.  **Flexible Colormaps:**
    -   Use `viridis` for sequential data or `coolwarm` for diverging data (like correlations ranging from -1 to 1).

---

### How to Build

The `D3Heatmap` widget accepts a pandas DataFrame where:

-   The **index** becomes the row labels
-   The **columns** become the column labels
-   The **values** in the cells are displayed as colors

This is ideal for correlation matrices generated with `df.corr()` or pivot tables.

#### Quick Example with Correlation Matrix

```python
import pandas as pd
from Isea.heatmap import D3Heatmap

# Create sample data
data = {
    "StockBEV": [100, 200, 150, 300, 250],
    "SalesBEV": [20, 45, 30, 80, 60],
    "ChargingStations": [50, 120, 80, 200, 150],
    "GDP": [500, 800, 600, 1200, 900],
}
df = pd.DataFrame(data)

# Calculate correlation matrix
corr_matrix = df.corr()

# Create heatmap
heatmap = D3Heatmap(
    df=corr_matrix,
    title="EV Metrics Correlation Matrix",
    cmap="coolwarm",
    width=500,
    height=400
)

heatmap
```

#### Quick Example with Custom Data

```python
import pandas as pd
from Isea.heatmap import D3Heatmap

# Create a pivot-style DataFrame
regions = ["Europe", "Asia", "Americas"]
metrics = ["Stock", "Sales", "Charging"]
values = [
    [85, 72, 68],
    [92, 88, 45],
    [60, 55, 78],
]

df = pd.DataFrame(values, index=regions, columns=metrics)

heatmap = D3Heatmap(
    df=df,
    title="Regional EV Performance",
    cmap="viridis",
    width=450,
    height=350
)

heatmap
```

---

### Available Configuration Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `df` | DataFrame | Pandas DataFrame with numeric values |
| `title` | str | Chart title displayed at the top |
| `cmap` | str | Color scheme: `"viridis"` (sequential) or `"coolwarm"` (diverging) |
| `width` | int | Chart width in pixels (default: 600) |
| `height` | int | Chart height in pixels (default: 400) |

---

### Analytical Questions This View Can Answer

-   Which metrics are strongly correlated with EV adoption?
-   Are there unexpected negative correlations in the data?
-   How do different regions compare across multiple dimensions?