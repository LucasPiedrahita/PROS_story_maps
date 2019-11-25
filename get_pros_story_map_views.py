from arcgis.gis import GIS, Item
from datetime import datetime
from calendar import month_name
import pandas as pd
import os
import logging

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Level for the whole logger

file_handler = logging.FileHandler("get_pros_story_map_views.log")
file_handler.setLevel(logging.INFO) # Level for this specific log file
file_formatter = logging.Formatter("%(asctime)s:%(name)s:Line %(lineno)d:%(levelname)s:: %(message)s")
file_handler.setFormatter(file_formatter)

stream_handler = logging.StreamHandler() # Prints to console rather than a file
stream_formatter = logging.Formatter("Line %(lineno)d:%(levelname)s:: %(message)s")
stream_handler.setFormatter(stream_formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logger.info("New execution of get_pros_story_map_views.py at {0}".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))

# Define variables
last_full_month = datetime.now().month - 1

# Define functions
def isWebApp(item):
    """ Return True if the ArcGIS item is the type 'Web Mapping Application' """
    logger.debug("isWebApp() input has type: {0}".format(type(item)))
    try:
        if isinstance(item, Item):
            return(item.type == "Web Mapping Application")
        else:
            raise TypeError("isWebApp(item) requires the item to have type = 'arcgis.gis.Item'")
    except TypeError:
        logger.exception("isWebApp(item) requires the item to have type = 'arcgis.gis.Item'")

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
    logger.debug("getUsageStats: {0}".format(usage_stats))
    return(usage_stats)

# Connect to AGOL & get list of live PROS story maps
try:
    gis = GIS("https://wake.maps.arcgis.com", os.environ.get("AGOL_USER"), os.environ.get("AGOL_PASS"))
    logger.debug("Connected to {0}".format(gis.url))
    storymaps_group = gis.groups.get("264e862549e24faca0bbc2ca92bc2dec")
    storymaps_live = list(filter(isWebApp, storymaps_group.content()))
except Exception as e:
    logger.exception("An error occurred while connecting to wake.maps.arcgis.com or finding story maps:")

#Loop through each story map and get its title, views during the last full month, and total views since its creation.
try:
    usage_stats_df = pd.DataFrame(columns=["TourTitle", "Month", "ViewsThisMonth", "TotalViewsSinceCreation"])
    for storymap in storymaps_live:
        usage_stats_df = usage_stats_df.append(getUsageStats(storymap, last_full_month), ignore_index=True)
    logger.info("Constructed usage_stats_df:\n{0}".format(usage_stats_df))
except Exception as e:
    logger.exception("An error occurred while getting story map usage stats:")

logger.info("Execution of get_pros_story_map_views.py completed at {0}\n\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
