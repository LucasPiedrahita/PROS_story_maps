from arcgis.gis import GIS, Item
from datetime import datetime
from dateutil.relativedelta import relativedelta
from calendar import month_name
import pandas as pd
import os
import traceback

# Logging config
txtFile = open("C:\\Users\\Lucas.Piedrahita\\OneDrive - Wake County\\LP\\JupyterNotebooks\\story_map_views\\get_pros_story_map_views.txt", "w")
txtFile.write("New execution of get_pros_story_map_views.py started at {0}\n\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))

# Define variables
one_month_ago = datetime.now() + relativedelta(months=-1)
last_full_month = one_month_ago.month
last_month_column_name = "{0}{1}Views".format(month_name[last_full_month], one_month_ago.year)
troubleshoot_email_list = ["Lucas.Piedrahita@wakegov.com", "Benjamin.Strauss@wakegov.com"]
full_email_list = troubleshoot_email_list.append("Ben.Wittenberg@wakegov.com")

# Define functions
def sendEmail(recipient_list, subject, message=""):
    pass

def connectToWakeGIS(url, username, password):
    """ Passes arguments to GIS() function while wrapping it in error trapping.
    Returns the GIS object if if successfully connects to wake.maps.arcgis.com
     """
    try:
        gis = GIS(url, username, password)
        if "user" not in gis.properties: 
            # This occurs if GIS() connects ananymously rather than as a user,
            # and probably means os.environ.get("AGOL_USER") and 
            # os.environ.get("AGOL_PASS") returned None.
            raise PermissionError("Logged into {0} anonymously and will therefore not be able to view usage stats of story maps.".format(gis.url))
    except PermissionError:
        traceback.print_exc(file=txtFile)
        txtFile.write("\nScript failed at {0} because necessary access to wake.maps.arcgis.com could not be established.\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
        txtFile.close() 
        sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", message="TxtFile")
        raise SystemExit
    except Exception as e:
        traceback.print_exc(file=txtFile)
        txtFile.write("\nAn unexpected error occurred while connecting to wake.maps.arcgis.com, causing the script to fail at {1}:\n{0}:\n".format(e, datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
        txtFile.close()
        sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", message="TxtFile")
        raise SystemExit
    else:
        txtFile.write("Connected to {0} as {1}\n\n".format(gis.url, gis.properties["user"]["username"]))
        return(gis)

def isWebApp(item):
    """ Return True if the ArcGIS item is the type 'Web Mapping Application', 
    otherwise return False """
    # txtFile.write("isWebApp() input has type: {0}\n".format(type(item)))
    if isinstance(item, Item):
        return(item.type == "Web Mapping Application")
    else:
        return(False)

def getLiveStorymaps(gis, isWebApp):
    """ Returns the list of story maps that are shared with the PROS Story Map Tours - Live
     """
    try:
        storymaps_group = gis.groups.get("264e862549e24faca0bbc2ca92bc2dec")
        storymaps_live = list(filter(isWebApp, storymaps_group.content()))
    except Exception as e:
        txtFile.write("An unexpected error occurred while retrieving story maps from the PROS Story Map Tours - Live group:\n{0}\n".format(e))
        traceback.print_exc(file=txtFile)
    else:
        return(storymaps_live)

def getUsageStats(storymap, month, last_month_column_name):
    """ Return object of the title, total views since creation,  
    and views during the pervious month, for an input of a Web Mapping 
    Application ArcGIS item, such as a storymap """
    # Get last 60 Days of usage stats
    try:
        usage_df = storymap.usage("60D")
    except IndexError:
        # This occurs for story maps younger than 60 days, where .usage("60D")
        # throws "IndexError: list index out of range" 
        views_last_full_month = "Unable to calculate. Please visit https://wake.maps.arcgis.com/home/item.html?id={0}#usage to get usage stats".format(storymap.id)
    else:
        # Filter to get only the rows from the last full month
        usage_last_full_month_df = usage_df[pd.DatetimeIndex(usage_df["Date"]).month == month]
        views_last_full_month = usage_last_full_month_df["Usage"].sum()
    finally:
        usage_stats = {
            "TourTitle": storymap.title,
            "TourId": storymap.id,
            "TotalViewsSinceCreation": storymap.numViews,last_month_column_name: views_last_full_month
            }
        return(usage_stats)

def verifyConstructedDf(usage_stats_df, last_month_column_name):
    """ Return a list of [True, why_it_succeeded] if the constructed usage stats 
    DataFrame looks to have been built correctly, otherwise return a list of 
    [False, why_it_failed]. """
    rows = usage_stats_df.shape[0]
    if rows < 1:
        result = False
        msg = "The usage_stats_df FAILED VERIFICATION because it is empty."
    else:
        failed_usage_stats_df = usage_stats_df[pd.to_numeric(usage_stats_df[last_month_column_name], errors='coerce').isnull()]
        failed_usage_stats_num = failed_usage_stats_df.shape[0]
        all_failed = failed_usage_stats_num == rows
        if all_failed:
            result = False
            msg = "The usage_stats_df FAILED VERIFICATION because none of the usage states could be calculated for the column, {}.".format(last_month_column_name)
        else:
            result = True
            msg = "The usage_stats_df was successfully verified to contain records and have at least one successfully calculated value for the {} column.".format(last_month_column_name)
    return([result, msg])

def constructUsageDf(storymaps_live, last_full_month, last_month_column_name, getUsageStats):
    """ Returns a pandas DataFrame consisting of the usage stats for each live story map.

    Loops through each story map in storymaps_live and gets its title, views during the last full month, and total views since its creation. """
    try:
        usage_stats_df = pd.DataFrame(columns=["TourTitle", "TourId", "TotalViewsSinceCreation", last_month_column_name])
        for storymap in storymaps_live:
            row = getUsageStats(storymap, last_full_month, last_month_column_name)
            usage_stats_df = usage_stats_df.append(row, ignore_index=True)
    except Exception as e:
        txtFile.write("An unexpected error occurred while constructing the usage stats dtaframe:\n{0}:\n".format(e))
        traceback.print_exc(file=txtFile)
        txtFile.write("This caused the script to fail at {2}.\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
        txtFile.close()
        sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", message="TxtFile")
        raise SystemExit
    else:
        verified, verification_msg = verifyConstructedDf(usage_stats_df, last_month_column_name)
        if verified:
            txtFile.write("{0}\n{1}\n".format(verification_msg, usage_stats_df))
            return(usage_stats_df)
        else:
            txtFile.write("{0}\n{1}\n\nThe script failed at {2} because the usage_stats_df DataFrame could not be verified.\n".format(verification_msg, usage_stats_df, datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
            txtFile.close()
            sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", message="TxtFile")
            raise SystemExit

# Run script:
gis = connectToWakeGIS("https://wake.maps.arcgis.com", os.environ.get("AGOL_USER"), os.environ.get("AGOL_PASS"))

storymaps_live = getLiveStorymaps(gis, isWebApp)

usage_stats_df = constructUsageDf(storymaps_live, last_full_month, last_month_column_name, getUsageStats)

subject = "PROS Story Maps Tours Usage Statistics for {0}, {1}".format(month_name[last_full_month], one_month_ago.year)
usage_stats_df_without_id = usage_stats_df.drop("TourId", axis=1)
message = "usage_stats_df_without_id"
sendEmail(recipient_list = full_email_list, subject = subject, message = message)

# Finish logging:
txtFile.write("\nExecution of get_pros_story_map_views.py completed at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
txtFile.close()
