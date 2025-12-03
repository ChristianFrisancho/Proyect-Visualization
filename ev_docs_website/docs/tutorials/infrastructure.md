# Tutorial: Infrastructure Alignment Analysis

This tutorial explains how to use the ScatterBrush to analyze the relationship between charging infrastructure and the size of the battery-electric vehicle (BEV) fleet.

![Infrastructure Alignment Demo](infraestructure_demo.gif)

### Configuration

Set the scatter plot axes as follows:
-   **X-axis:** `ChargingStations`
-   **Y-axis:** `StockBEV`

### Interpretation

This view helps assess whether the deployment of public charging infrastructure is keeping pace with the growth of the BEV fleet. The `y=x` diagonal represents a 1:1 ratio of public chargers to BEVs.

> -   **Well above the diagonal (High Y/X Ratio):** The number of BEVs far exceeds the number of public chargers. This may indicate a reliance on private home charging or a potential infrastructure bottleneck.
> -   **Near the diagonal (Moderate Ratio):** Infrastructure deployment is roughly keeping pace with fleet growth.
> -   **Below the diagonal (Low Y/X Ratio):** There are more public chargers than BEVs. This often signals a policy-driven effort to "overbuild" infrastructure to stimulate future adoption.

---

### Step-by-Step Analysis Example

#### Question: How does the infrastructure-to-vehicle ratio compare across different vehicle types, and how has it changed over time?

*   **Method:**
    1.  Set the axes to `ChargingStations` (X) and `StockBEV` (Y).
    2.  Activate the **x=y** button.
    3.  Move the time slider from the earliest year to the latest, observing how different modes move in relation to the diagonal.
    4.  Use the legend to filter by `Cars`, `Vans`, and `Buses` individually to see their patterns more clearly.
*   **Answer:**
    *   **Cars:** Almost always have a moderate to high ratio (above the diagonal), which is expected since many owners rely on home charging. Countries near or below the line demonstrate an exceptionally strong government push for public infrastructure.
    *   **Buses:** Are not relevant in this view, as they typically use private, depot-based charging, not the public network measured here.
    *   **Vans & Trucks:** In the early years, some commercial vehicles show moderate ratios. However, as time progresses, they tend to fall further below the diagonal. This suggests that for commercial fleets, the availability of *public* chargers becomes less of a determining factor for adoption, and other factors (e.g., total cost of ownership, depot charging solutions, vehicle availability) are more critical.