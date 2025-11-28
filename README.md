# Proyect-Visualization
OPTION 1:

STEP 1: Run this commands on terminal:

pip install -U pip

pip install anywidget traitlets

pip install -e .

run P6_deliverable_final.ipynb

OPTION 2(more easy):

Step 1 — Open Colab

1. Go to 👉 [https://colab.research.google.com](https://colab.research.google.com)

2. Create a new collab

3. Run this commands on collab:

!pip install -q isea-vis==0.1.1

!pip install pycountry_convert

!pip install country_converter

Step 2 — Upload and load the dataset

You must upload your data file to Colab.  
Assume your dataset is called `Global_EV_clean.csv`:

1. In the left sidebar in Colab, open the Files tab.  
2. Click the "upload icon" and select your local CSV file.  
3. Verify that the file appears under `/content` in the file list.

Now create a new cell in Colab and paste:


import pandas as pd

Load the dataset
```python
df = pd.read_csv("Global_EV_clean.csv")
```

Check that it was loaded correctly
```python
print("✅ File loaded successfully. Shape (rows, columns):", df.shape)
df.head()
```

Step 3 — Basic exploratory analysis

Create another cell and paste:

```python
df.info()
print("\nMissing values per column:")
print(df.isnull().sum())
df.describe()
```

This gives you a quick overview of the structure and quality of your data.

Step 4 — Descriptive visualizations

Initial plots to understand the global distribution of the data:

```python
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(10, 5))
sns.histplot(df['Year'], bins=20, kde=True)
plt.title("Distribution of records per year")
plt.xlabel("Year")
plt.ylabel("Frequency")
plt.show()

plt.figure(figsize=(12, 6))
top_countries = df['Country'].value_counts().head(10)
sns.barplot(x=top_countries.index, y=top_countries.values)
plt.title("Top 10 countries with the most EV records")
plt.ylabel("Number of records")
plt.xticks(rotation=45)
plt.show()

```

Step 5 — Global interactive map with isea-vis

```python
scatter = isea.scatter(
    data=df,
    x='Year',
    y='EV_Share',       # <- change if your dataset uses another name
    color='Country',
    size='EV_Sales',    # <- change if your dataset uses another name
    title='Global evolution of electric vehicles'
)

scatter
```

Step 6 — “World Line Chart” map

Create a new cell and paste:

```python
chart = isea.worldmaplinechart(
    data=df,
    geo_key='Country',
    x='Year',
    y='EV_Share',
    title='EV market share trend by country'
)

chart
```


Step 7 — "Energy Quad" multidimensional visualization

Create another cell and paste:
```python
quad = isea.energyquad(
    data=df,
    x='EV_Sales',
    y='EV_Share',
    color='Region',
    size='Population',  # <- if your dataset has a 'Population' column
    title='Relationship between EV sales, market share and region'
)

quad
```


Step 8 — Comparative line chart with Plotly

Create a new cell and paste:

```python
import plotly.express as px

fig = px.line(
    df,
    x="Year",
    y="EV_Share",
    color="Country",
    title="Evolution of electric vehicle market share by country"
)

fig.show()

```

This will create an interactive line chart comparing EV market share over time by country.

