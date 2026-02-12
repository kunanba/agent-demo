# Sample Images

Place financial charts, graphs, and document images here for vision analysis.

## Suggested Test Images

1. **Revenue Charts**
   - Line charts showing revenue trends
   - Bar charts comparing quarters

2. **Financial Tables**
   - Balance sheet screenshots
   - Income statement tables

3. **Performance Graphs**
   - Profit margin trends
   - Stock price charts
   - Market share pie charts

## Creating Test Images

You can create simple charts using:

**Python (matplotlib)**:
```python
import matplotlib.pyplot as plt

quarters = ['Q1', 'Q2', 'Q3', 'Q4']
revenue = [180, 195, 205, 220]

plt.figure(figsize=(10, 6))
plt.plot(quarters, revenue, marker='o')
plt.title('Revenue Trend - 2023')
plt.ylabel('Revenue ($M)')
plt.savefig('revenue_chart.png')
```

**Excel**:
1. Create data table
2. Insert chart
3. Export as image

## Using Images in the Agent

Upload images via the Streamlit UI sidebar or reference them in queries:

```python
from src.tools.vision_tool import VisionTool

vision = VisionTool()
result = vision(
    image_path="data/images/revenue_chart.png",
    query="What is the revenue trend?",
    analysis_type="chart"
)
```
