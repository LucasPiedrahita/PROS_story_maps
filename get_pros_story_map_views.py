from arcgis.gis import GIS, Item
from datetime import datetime
from calendar import month_name
import pandas as pd
import os
import traceback

# Logging config
txtFile = open("C:\\Users\\Lucas.Piedrahita\\OneDrive - Wake County\\LP\\JupyterNotebooks\\story_map_views\\get_pros_story_map_views.txt", "w")
txtFile.write("New execution of get_pros_story_map_views.py started at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))

# Define variables
last_full_month = datetime.now().month - 1
last_month_column_name = "{0}Views".format(month_name[last_full_month])

# Define functions
def isWebApp(item):
    """ Return True if the ArcGIS item is the type 'Web Mapping Application' """
    # txtFile.write("isWebApp() input has type: {0}\n".format(type(item)))
    try:
        if isinstance(item, Item):
            return(item.type == "Web Mapping Application")
        else:
            raise TypeError("isWebApp(item) requires the item to have type = 'arcgis.gis.Item'")
    except TypeError:
        txtFile.write("\nisWebApp(item) requires the item to have type = 'arcgis.gis.Item'\n")
        traceback.print_exc(file=txtFile)


def getUsageStats(storymap, month, last_month_column_name):
    """ Return object of the title, previous month, views during the pervious month, 
    and total views since creation for an input of a storymap ArcGIS item """
    usage_df = storymap.usage("60D")
    usage_last_full_month_df = usage_df[pd.DatetimeIndex(usage_df["Date"]).month == month]
    views_last_full_month = usage_last_full_month_df["Usage"].sum()
    usage_stats = {
        "TourTitle": storymap.title,
        "TotalViewsSinceCreation": storymap.numViews,
        last_month_column_name: views_last_full_month
        }
    # txtFile.write("getUsageStats: {0}\n".format(usage_stats))
    return(usage_stats)

# Connect to AGOL & get list of live PROS story maps
try:
    gis = GIS("https://wake.maps.arcgis.com", os.environ.get("AGOL_USER"), os.environ.get("AGOL_PASS"))
    txtFile.write("Connected to {0}\n".format(gis.url))
    storymaps_group = gis.groups.get("264e862549e24faca0bbc2ca92bc2dec")
    storymaps_live = list(filter(isWebApp, storymaps_group.content()))
except Exception as e:
    txtFile.write("\nAn error occurred while connecting to wake.maps.arcgis.com or finding story maps:\n")
    traceback.print_exc(file=txtFile)

#Loop through each story map and get its title, views during the last full month, and total views since its creation.
try:
    usage_stats_df = pd.DataFrame(columns=["TourTitle", "TotalViewsSinceCreation", last_month_column_name])
    for storymap in storymaps_live:
        usage_stats_df = usage_stats_df.append(getUsageStats(storymap, last_full_month, last_month_column_name), ignore_index=True)
    txtFile.write("Constructed usage_stats_df:\n{0}\n".format(usage_stats_df))
except Exception as e:
    txtFile.write("\nAn error occurred while getting story map usage stats:\n")
    traceback.print_exc(file=txtFile)

txtFile.write("\nExecution of get_pros_story_map_views.py completed at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
txtFile.close()