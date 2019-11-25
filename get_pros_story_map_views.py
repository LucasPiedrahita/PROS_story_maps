from arcgis.gis import GIS
from datetime import datetime
from calendar import month_name
import requests
import re
import pandas as pd
import os

# Define variables
today = datetime.now()
last_full_month = today.month - 1

# Define functions
def isWebApp(item):
    """ Return True if the ArcGIS item is the type 'Web Mapping Application' """
    return(item.type == "Web Mapping Application")

def getUsageStats(storymap, month):
    """ Return object of the title, previous month, views during the pervious month, 
    and total views since creation for an input of a storymap ArcGIS item """
    usage_df = storymap.usage("60D")
    usage_last_full_month_df = usage_df[pd.DatetimeIndex(usage_df["Date"]).month == month]
    views_last_full_month = usage_last_full_month_df["Usage"].sum()
    usage_stats = {
        "TourTitle": storymap.title,
        "Month": month_name[month],
        "ViewsThisMonth": views_last_full_month,
        "TotalViewsSinceCreation": storymap.numViews
        }
    return(usage_stats)

try:
    # Connect to AGOL & get list of live PROS story maps
    gis = GIS("https://www.arcgis.com", os.environ.get("AGOL_USER"), os.environ.get("AGOL_PASS")) 
    print("Connected to {0}".format(gis.url))
    storymaps_group = gis.groups.get("264e862549e24faca0bbc2ca92bc2dec")
    storymaps_live = list(filter(isWebApp, storymaps_group.content()))
except Exception as e:
    print("An error occurred while connecting to wake.maps.arcgis.com or finding story map groups: {0}".format(e))

try:
    #Loop through each story map and get its title, views during the last full month, and total views since its creation.
    usage_stats_df = pd.DataFrame(columns=["TourTitle", "Month", "ViewsThisMonth", "TotalViewsSinceCreation"])
    for storymap in storymaps_live:
        usage_stats_df = usage_stats_df.append(getUsageStats(storymap, 14), ignore_index=True)
    print(usage_stats_df)
except Exception as e:
    print("An error occurred while getting story map usage stats: {0}".format(e))
