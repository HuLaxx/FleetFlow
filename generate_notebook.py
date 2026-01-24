
import json
import os

notebook_content = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# FleetFlow - Exploratory Data Analysis (EDA)\n",
    "\n",
    "This notebook performs an initial exploratory analysis of the FleetFlow delivery data. We analyze order patterns, driver availability, and geospatial distributions to inform our optimization algorithms.\n",
    "\n",
    "## Objectives\n",
    "1. **Demand Analysis**: Understand peak ordering times.\n",
    "2. **Geospatial Distribution**: Visualize where orders are clustered.\n",
    "3. **Driver Metrics**: Analyze driver ratings and availability.\n",
    "\n",
    "---"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "from sqlalchemy import create_engine\n",
    "import os\n",
    "from dotenv import load_dotenv\n",
    "\n",
    "# Set plotting style\n",
    "sns.set_style(\"whitegrid\")\n",
    "plt.rcParams['figure.figsize'] = (12, 6)\n",
    "\n",
    "# Load environment variables\n",
    "load_dotenv('../.env')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Data Connection\n",
    "Connecting to the local PostgreSQL/TimescaleDB instance."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "DB_USER = os.getenv(\"POSTGRES_USER\", \"fleetflow\")\n",
    "DB_PASS = os.getenv(\"POSTGRES_PASSWORD\", \"fleetflow_dev\")\n",
    "DB_HOST = os.getenv(\"POSTGRES_HOST\", \"localhost\")\n",
    "DB_PORT = os.getenv(\"POSTGRES_PORT\", \"5432\")\n",
    "DB_NAME = os.getenv(\"POSTGRES_DB\", \"fleetflow\")\n",
    "\n",
    "DATABASE_URL = f\"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}\"\n",
    "engine = create_engine(DATABASE_URL)\n",
    "print(f\"Connected to {DB_NAME} at {DB_HOST}\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Load Data\n",
    "Fetching `orders` and `drivers` for analysis."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "query_orders = \"SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL '30 days'\"\n",
    "df_orders = pd.read_sql(query_orders, engine)\n",
    "\n",
    "query_drivers = \"SELECT * FROM drivers\"\n",
    "df_drivers = pd.read_sql(query_drivers, engine)\n",
    "\n",
    "print(f\"Orders Loaded: {df_orders.shape}\")\n",
    "print(f\"Drivers Loaded: {df_drivers.shape}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "df_orders['created_at'] = pd.to_datetime(df_orders['created_at'])\n",
    "df_orders['hour'] = df_orders['created_at'].dt.hour\n",
    "df_orders.head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Demand Analysis\n",
    "Visualizing order volume by hour of day."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "plt.figure(figsize=(14, 6))\n",
    "sns.histplot(data=df_orders, x='hour', bins=24, kde=True, color='skyblue')\n",
    "plt.title('Order Distribution by Hour of Day')\n",
    "plt.xlabel('Hour (0-23)')\n",
    "plt.ylabel('Number of Orders')\n",
    "plt.axvline(df_orders['hour'].mean(), color='red', linestyle='--', label=f'Mean Hour: {df_orders[\"hour\"].mean():.1f}')\n",
    "plt.legend()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. Driver Performance\n",
    "Analyzing the distribution of driver ratings."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "plt.figure(figsize=(10, 5))\n",
    "sns.countplot(data=df_drivers, x='rating', palette='viridis')\n",
    "plt.title('Driver Rating Distribution')\n",
    "plt.xlabel('Rating (1-5)')\n",
    "plt.ylabel('Count')\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 5. Geospatial Overview\n",
    "Plotting delivery locations to identify hotspots."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Simple scatter plot of lat/lon\n",
    "plt.figure(figsize=(10, 10))\n",
    "sns.scatterplot(data=df_orders, x='delivery_lon', y='delivery_lat', alpha=0.6, hue='hour', palette='coolwarm')\n",
    "plt.title('Geospatial Distribution of Delivery Locations')\n",
    "plt.xlabel('Longitude')\n",
    "plt.ylabel('Latitude')\n",
    "plt.show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open("notebooks/01_exploratory_data_analysis.ipynb", "w") as f:
    json.dump(notebook_content, f, indent=1)
    
print("Notebook created successfully.")
