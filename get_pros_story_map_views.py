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
last_day_of_last_month = datetime.now().replace(day=1) - timedelta(days=1)
last_month_column_name = "{0} Views".format(last_day_of_last_month.strftime("%B %Y"))
AGOL_USER = os.environ.get("AGOL_USER")
AGOL_PASS = os.environ.get("AGOL_PASS")
storymap_group_id = "264e862549e24faca0bbc2ca92bc2dec"
from_address = "no.reply@wakegov.com"
troubleshoot_email_list = ["Lucas.Piedrahita@wakegov.com"]
full_email_list = ["Lucas.Piedrahita@wakegov.com"]
msg = MIMEMultipart()
msg["From"] = from_address

# Define functions
def logMsg(message):
    print(message, end="")
    txtFile.write(message)

def sendEmail(recipient_list, subject, body, text_type):
    logMsg("\nEMAIL SENT:\n'''\nTo: {0}\nSubject: {1}\nBody:\n{2}\n'''\nEnd of EMAIL SENT.\n".format(", ".join(recipient_list), subject, body))
    msg["Subject"] = subject
    msg["To"] = ", ".join(recipient_list)
    msg.attach(MIMEText(body, text_type))
    emailbody = msg.as_string()
    # emailserver = smtplib.SMTP("smtprelay.wakegov.com")
    # emailserver.sendmail(from_address, ", ".join(recipient_list), emailbody)
    # emailserver.quit()

def logError(message):
    logMsg(message)
    sendEmail(troubleshoot_email_list, "Script get_pros_story_map_views.py failed", message, "plain")

def getUsageStats(storymap):
    """ Return object of the title, id, total views since creation,  
    and views during the previous month, for an input of a Web Mapping 
    Application ArcGIS item, such as a storymap """
    try:
        usage_df = storymap.usage("60D")
    except IndexError:
        # This occurs for story maps younger than 60 days, where .usage("60D") throws "IndexError: list index out of range" 
        views_last_full_month = "Storymap too young"
    else:
        # Filter to get only the rows from the last full month
        usage_last_full_month_df = usage_df[pd.DatetimeIndex(usage_df["Date"]).month == last_day_of_last_month.month]
        views_last_full_month = usage_last_full_month_df["Usage"].sum()
    finally:
        usage_stats = {
            "Tour Title": storymap.title,
            "Tour ID": storymap.id,
            "Total Views Since Creation": storymap.numViews,
            last_month_column_name: views_last_full_month
            }
        return(usage_stats)

# Run script:
try:
    try:
        # Connect to GIS
        gis = GIS("https://wake.maps.arcgis.com", AGOL_USER, AGOL_PASS)
        logMsg("Connected to {0} as {1}\n\n".format(gis.url, gis.properties["user"]["username"]))
    except:
        logError("ERROR occurred while connecting to wake.maps.arcgis.com:\n{0}\n".format(traceback.format_exc()))
    else:
        try:
            # Get storymaps from group
            storymaps_group = gis.groups.get(storymap_group_id)
            # Filter content in group to only get story maps and not maps & feature layers
            storymaps = list(filter(lambda item: (item.type == "Web Mapping Application"), storymaps_group.content()))
            logMsg("Story maps retrieved from the PROS Story Map Tours - Live group\n\n")
        except:
            logError("ERROR occurred while retrieving story maps from the PROS Story Map Tours - Live group:\n{0}\n".format(traceback.format_exc()))
        else:
            try:
                # Construct usage stats dataframe
                usage_stats_df = pd.DataFrame(columns=["Tour Title", "Tour ID", "Total Views Since Creation", last_month_column_name])
                for storymap in storymaps:
                    row = getUsageStats(storymap)
                    usage_stats_df = usage_stats_df.append(row, ignore_index=True)
            except:
                logError("ERROR occurred while constructing the usage stats dataframe:\n{0}:\n".format(traceback.format_exc()))
            else:
                # Check if usage stats dataframe is empty 
                num_storymaps = usage_stats_df.shape[0]
                if num_storymaps < 1:
                    logError("ERROR: The usage_stats_df FAILED VERIFICATION because it is empty: \n{0}\n".format(usage_stats_df))
                else:
                    # Check if the usage stats for the last month failed to be retrieved for every storymap
                    usage_stats_df_failed = usage_stats_df[pd.to_numeric(usage_stats_df[last_month_column_name], errors='coerce').isnull()]
                    num_storymaps_failed = usage_stats_df_failed.shape[0]
                    some_failed = num_storymaps_failed > 0
                    all_failed = num_storymaps_failed == num_storymaps
                    if all_failed:
                        logError("ERROR: The usage_stats_df FAILED VERIFICATION because none of the usage stats could be retrieved for the column, {0}.\n{1}\n".format(last_month_column_name, usage_stats_df))
                    else:
                        # Send email to full email list
                        logMsg("The usage_stats_df was verified to contain records and have at least one successfully retrieved value for the {0} column:\n{1}\n".format(last_month_column_name, usage_stats_df))
                        subject = "PROS Story Map Tours Usage for {0}".format(last_day_of_last_month.strftime("%B, %Y"))
                        usage_stats_df_formatted = usage_stats_df.drop("Tour ID", axis=1).to_html(index=False)                   
                        style = """table {
                        border: 1px solid #1C6EA4 !important;
                        width: 620px;
                        border-collapse: collapse;
                        }
                        table td, table th {
                        border: 1px solid #AAAAAA;
                        padding: 3px 3px;
                        }
                        table thead th {
                        font-weight: bold;
                        background: #458DBA;
                        color: #FFFFFF;
                        border-left: 2px solid #D0E4F5;
                        }
                        """
                        manual_check_sentence = ""
                        if some_failed:
                            # Include sentence about manually checking usage if some failed to be retrieved
                            manual_check_sentence = "If your tour is younger than 60-days-old, please email Ben Wittenberg (Ben.Wittenberg@wakegov.com) or Lucas Piedrahita (Lucas.Piedrahita@wakegov.com) and ask that they retrieve the usage stats manually.<br><br>"
                        message = """\
                        <html>
                        <head>
                        <style>
                        {0}
                        </style>
                        </head>
                        <body>
                            <p>The monthly PROS story map tours usage report for {1} can be seen below:<br>
                            <br>
                            {2}
                            <br>
                            {3}
                            This is an automated email. Do not reply directly. If you have questions about this email or report, please email {4}.<br>
                            <br>
                            </p>
                        </body>
                        </html>
                        """.format(style, last_day_of_last_month.strftime("%B, %Y"), usage_stats_df_formatted, manual_check_sentence, " or ".join(troubleshoot_email_list))
                        
                        sendEmail(full_email_list, subject, message, "html")
except:
    # If an unexpected/uncaught error is thrown
    logError("\nScript failed unexpectedly at {0}:\n{1}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), traceback.format_exc()))
    txtFile.close()
else:
    logMsg("\nExecution of get_pros_story_map_views.py completed at {0}\n".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))
    txtFile.close()
