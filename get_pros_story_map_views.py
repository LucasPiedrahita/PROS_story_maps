from arcgis.gis import GIS
from datetime import datetime, timedelta
import pandas as pd
import os
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Logging config
txtFile = open("C:\\Users\\Lucas.Piedrahita\\OneDrive - Wake County\\LP\\JupyterNotebooks\\story_map_views\\get_pros_story_map_views.txt", "w")
txtFile.write("New execution of get_pros_story_map_views.py started at {0}\n\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))

# Define variables
today = datetime.now()
first_of_this_month = today.replace(day=1)
last_day_of_last_month = first_of_this_month - timedelta(days=1)
last_full_month = last_day_of_last_month.month
last_month_column_name = "{0}Views".format(last_day_of_last_month.strftime("%B%Y"))

from_address = "no.reply@wakegov.com"
troubleshoot_email_list = ["Lucas.Piedrahita@wakegov.com", "Benjamin.Strauss@wakegov.com"]
full_email_list = troubleshoot_email_list.append("Ben.Wittenberg@wakegov.com")
msg = MIMEMultipart()
msg["From"] = from_address

# Define functions
def sendEmail(recipient_list, subject, body):
    # msg["Subject"] = subject
    # msg["To"] = ", ".join(recipient_list)
    # msg.attach(MIMText(body, 'plain'))
    # emailbody = msg.as_string()
    
    # emailserver = stmplib.SMTP("smtprelay.wakegov.com")
    # emailserver.sendmail(from_address, ", ".join(recipient_list), emailbody)
    # emailserver.quit()
    pass

def getLiveStorymaps(gis):
    """ Returns the list of story maps that are shared with the PROS Story Map Tours - Live
     """
    try:
        storymaps_group = gis.groups.get("264e862549e24faca0bbc2ca92bc2dec")
        # Filter content in group to only get story maps and not maps & feature layers
        storymaps_live = list(filter(lambda item: (item.type == "Web Mapping Application"), storymaps_group.content()))
    except Exception as e:
        txtFile.write("An unexpected error occurred while retrieving story maps from the PROS Story Map Tours - Live group:\n{0}\n".format(e))
        traceback.print_exc(file=txtFile)
    else:
        txtFile.write("Story maps retrieved from the PROS Story Map Tours - Live group\n\n")
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
        views_last_full_month = "Storymap too young. Please visit https://wake.maps.arcgis.com/home/item.html?id={0}#usage to get usage stats manually".format(storymap.id)
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
        msg = "Error: The usage_stats_df FAILED VERIFICATION because it is empty."
    else:
        failed_usage_stats_df = usage_stats_df[pd.to_numeric(usage_stats_df[last_month_column_name], errors='coerce').isnull()]
        failed_usage_stats_num = failed_usage_stats_df.shape[0]
        all_failed = failed_usage_stats_num == rows
        if all_failed:
            result = False
            msg = "Error: The usage_stats_df FAILED VERIFICATION because none of the usage states could be calculated for the column, {}.".format(last_month_column_name)
        else:
            result = True
            msg = "The usage_stats_df was successfully verified to contain records and have at least one successfully calculated value for the {} column:".format(last_month_column_name)
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
        sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", body="TxtFile")
        raise SystemExit
    else:
        verified, verification_msg = verifyConstructedDf(usage_stats_df, last_month_column_name)
        if verified:
            txtFile.write("{0}\n{1}\n".format(verification_msg, usage_stats_df))
            return(usage_stats_df)
        else:
            txtFile.write("{0}\n{1}\n\nThe script failed at {2} because the usage_stats_df DataFrame could not be verified.\n".format(verification_msg, usage_stats_df, datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
            txtFile.close()
            sendEmail(recipient_list=troubleshoot_email_list, subject="get_pros_story_map_views.py FAILED", body="TxtFile")
            raise SystemExit

# Run script:
gis = GIS("https://wake.maps.arcgis.com", os.environ.get("AGOL_USER"), os.environ.get("AGOL_PASS"))

storymaps_live = getLiveStorymaps(gis)

usage_stats_df = constructUsageDf(storymaps_live, last_full_month, last_month_column_name, getUsageStats)

subject = "PROS Story Maps Tours Usage Statistics for {0}".format(last_day_of_last_month.strftime("%B, %Y"))
usage_stats_df_without_id = usage_stats_df.drop("TourId", axis=1)
message = "usage_stats_df_without_id"
sendEmail(full_email_list, subject, message)

# Finish logging:
txtFile.write("\nExecution of get_pros_story_map_views.py completed at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
txtFile.close()
