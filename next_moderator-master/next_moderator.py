import random
import base64
import pandas as pd
import numpy as np
import streamlit as st
import datetime as dt
import altair as alt
from azure.storage.blob import BlobServiceClient
import io

# ================= #
#  AZURE FUNCTIONS  #
# ================= #


# Azure credentials
connection_string = st.secrets.blob_credentials.connection_string
container_name = st.secrets.blob_credentials.container_name


def read_from_blob_storage(file_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=file_name
    )
    downloaded_blob = blob_client.download_blob().readall()
    return downloaded_blob


def prepare_xlsx_for_upload(tuples_list):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    for x in tuples_list:
        x[0].to_excel(writer, sheet_name=x[1], index=False)
    writer.close()
    return output.getvalue()


def upload_to_blob_storage(tuples_list, file_name):
    file_path = prepare_xlsx_for_upload(tuples_list)
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=file_name
    )
    blob_client.upload_blob(file_path, overwrite=True)


# ===================== #
#  STREAMLIT FUNCTIONS  #
# ===================== #


# get list of previous moderators
@st.cache_data  # to only run this function once at the beginning instead of with every click
def get_data():
    blob_file = read_from_blob_storage("moderators.xlsx")

    moderators_df = pd.read_excel(blob_file, sheet_name="moderators")
    standup_df = pd.read_excel(blob_file, sheet_name="standup_history")
    retro_df = pd.read_excel(blob_file, sheet_name="retrospective_history")

    standup_df["date"] = pd.to_datetime(standup_df["date"], format="%Y-%m-%d").dt.date
    retro_df["date"] = pd.to_datetime(retro_df["date"], format="%Y-%m-%d").dt.date
    return moderators_df, standup_df, retro_df


# randomize the next moderator
def get_next_mod(df, available_team, threshold):
    prev_mod = df.unique().tolist()[:threshold]
    next_mod = random.choice(available_team)
    while next_mod in prev_mod:
        next_mod = random.choice(available_team)
    return next_mod


# add the next moderator to the previous moderators list
def add_next_mod(df, next_mod, next_date):
    insert_row = {
        "date": next_date,
        "moderator": next_mod,
    }
    df = pd.concat([df, pd.DataFrame([insert_row])], ignore_index=True)
    standup_df["date"] = pd.to_datetime(standup_df["date"], format="%Y-%m-%d").dt.date
    return df


# =============== #
#  STREAMLIT APP  #
# =============== #


# set the page title, icon, and layout
st.set_page_config(page_title="Next Moderator", page_icon="📣", layout="wide")

# this aligns all buttons to the center of the container
customized_button = st.markdown(
    """<style >.stDownloadButton, div.stButton {text-align:center}</style>""",
    unsafe_allow_html=True,
)

# this hides the dataframe index column
hide_table_row_index = """<style> thead tr th:first-child {display:none} tbody th {display:none} </style>"""


col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    file_ = open("files/enpal_logo.png", "rb")
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")
    file_.close()
    st.markdown(
        f"""<p style='text-align:left;'>
        <img src='data:image/gif;base64,{data_url}' height=32></p>""",
        unsafe_allow_html=True,
    )
with col2:
    file_ = open("files/nm_logo.png", "rb")
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")
    file_.close()
    st.markdown(
        f"""<p style='text-align:center;'>
        <img src='data:image/gif;base64,{data_url}' height=32></p>""",
        unsafe_allow_html=True,
    )
with col3:
    selectbox_page = st.selectbox(
        "",
        ["☀️ Standups", "🪩 Retrospectives", "😎 Moderators"],
        label_visibility="collapsed",
    )

moderators_df, standup_df, retro_df = get_data()

if selectbox_page == "☀️ Standups":
    moderators = moderators_df["moderator"][moderators_df["is_active"] == True].tolist()
    last_mod = standup_df["moderator"].iloc[-1]
    last_date = standup_df["date"].iloc[-1]
    today = dt.datetime.date(dt.datetime.today())

    # shut down tool on Saturdays and Sundays, otherwise set default next moderation date
    # default next moderation date will default to next Monday, Wednesday, or Friday, whichever is closest
    if today.isoweekday() == 6:
        st.markdown(
            "<p style='text-align: center; font-size: 50px; color: #072543'><b>Tool is under contract, and Saturdays are off!</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 75px'><b>🛌</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 25px; color: #FFB000'><b>Next Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
    elif today.isoweekday() == 7:
        st.markdown(
            "<p style='text-align: center; font-size: 50px; color: #072543'><b>Tool is under contract, and Sundays are off!</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 75px'><b>🛌",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 25px; color: #FFB000'><b>Next Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
    else:
        if today.isoweekday() in [1, 2]:
            next_date_default = today + dt.timedelta(days=(3 - today.isoweekday()))
        elif today.isoweekday() in [3, 4]:
            next_date_default = today + dt.timedelta(days=(5 - today.isoweekday()))
        elif today.isoweekday() == 5:
            next_date_default = today + dt.timedelta(days=3)

        if today == last_date:
            top_label = "Today"
        else:
            top_label = f"{last_date} Stand-Up"
        st.markdown(
            f"<p style='text-align: center; font-size: 25px; color: #FFB000'><b>{top_label}'s Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([4, 1])
        with col1:
            available_team = st.multiselect(
                "Who is available to moderate?",
                moderators,
                moderators,
            )
        with col2:
            next_date = st.date_input("Next Stand-Up's Date", next_date_default)

        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            button_next_mod = st.button(label="Get Lucky!")
        with col3:
            checkbox_save = st.checkbox("Save Results", True)

        st.write("")

        # if button is clicked, get the next moderator and show some stats
        if button_next_mod:
            # clear cache at the beginning of the instance
            st.cache_data.clear()

            # some fool proofing
            if len(available_team) < 1:
                st.markdown(
                    "<p style='text-align: center; font-size: 70px'><b>🤔</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align: center; font-size: 35px; color: #072543'><b>Select at least one team member!</b></p>",
                    unsafe_allow_html=True,
                )
            elif len(available_team) == 1:
                st.markdown(
                    "<p style='text-align: center; font-size: 35px; color: #072543'><b>There's only one team member available... Why did you even run this thing?</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align: center; font-size: 70px'><b>🤨</b></p>",
                    unsafe_allow_html=True,
                )
            else:
                if last_date == next_date:
                    standup_df = standup_df[standup_df["date"] < next_date]
                    next_mod = get_next_mod(
                        standup_df["moderator"][::-1], available_team, 1
                    )
                    if checkbox_save:
                        standup_df = add_next_mod(standup_df, next_mod, next_date)
                        save_data = [
                            (moderators_df, "moderators"),
                            (standup_df, "standup_history"),
                            (retro_df, "retrospective_history"),
                        ]
                        upload_to_blob_storage(save_data, "moderators.xlsx")
                else:
                    next_mod = get_next_mod(
                        standup_df["moderator"][::-1], available_team, 1
                    )
                    if checkbox_save:
                        standup_df = add_next_mod(standup_df, next_mod, next_date)
                        save_data = [
                            (moderators_df, "moderators"),
                            (standup_df, "standup_history"),
                            (retro_df, "retrospective_history"),
                        ]
                        upload_to_blob_storage(save_data, "moderators.xlsx")

                st.markdown(
                    f"<p style='text-align: center; font-size: 25px; color: #FFB000'><b>{next_date} Stand-Up's Moderator</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='text-align: center; font-size: 75px; color: #072543'><b>{next_mod}</b></p>",
                    unsafe_allow_html=True,
                )
                st.write("")

                standup_plot_df = pd.merge(
                    standup_df, moderators_df, how="left", on="moderator"
                )
                standup_plot_df.rename(
                    columns={"date": "Date", "moderator": "Moderator"}, inplace=True
                )

                col1, col2, col3 = st.columns([2, 1, 2])
                # current month's leaderboard
                with col1:
                    st.markdown(
                        f"<p style='text-align: center; font-size: 20px; color: #072543'><b>This Month's Leaderboard</b></p>",
                        unsafe_allow_html=True,
                    )
                    leaderboard_this_month_df = standup_plot_df[
                        (standup_plot_df["Date"] >= dt.date(today.year, today.month, 1))
                        & (standup_plot_df["Date"] < next_date_default)
                    ]
                    leaderboard_this_month_df = leaderboard_this_month_df.groupby(
                        "Moderator", as_index=False
                    ).count()
                    leaderboard_this_month_df.rename(
                        columns={"Date": "Number of Moderations"}, inplace=True
                    )
                    leaderboard_this_month_df["Colour"] = np.where(
                        leaderboard_this_month_df["Number of Moderations"]
                        == leaderboard_this_month_df["Number of Moderations"].max(),
                        "#FFB000",
                        "#072543",
                    )
                    domain = leaderboard_this_month_df["Moderator"].tolist()
                    range = leaderboard_this_month_df["Colour"].tolist()
                    chart_data = (
                        alt.Chart(leaderboard_this_month_df)
                        .mark_bar()
                        .encode(
                            x="Moderator",
                            y=alt.Y(
                                "Number of Moderations", axis=alt.Axis(tickMinStep=1)
                            ),
                            color=alt.Color(
                                "Moderator",
                                scale=alt.Scale(domain=domain, range=range),
                                legend=None,
                            ),
                        )
                    )
                    st.altair_chart(chart_data, use_container_width=True)
                # recent moderators table
                with col2:
                    st.markdown(
                        f"<p style='text-align: center; font-size: 20px; color: #072543'><b>Previous moderators</b></p>",
                        unsafe_allow_html=True,
                    )
                    standup_display_df = (
                        standup_plot_df[standup_plot_df["Date"] < next_date_default][
                            ["Date", "Moderator"]
                        ]
                        .iloc[::-1]
                        .head(8)
                    )
                    st.markdown(hide_table_row_index, unsafe_allow_html=True)
                    st.table(standup_display_df)
                # overall leaderboard
                with col3:
                    st.markdown(
                        f"<p style='text-align: center; font-size: 20px; color: #072543'><b>All Time Leaderboard</b></p>",
                        unsafe_allow_html=True,
                    )
                    leaderboard_all_time_df = (
                        standup_plot_df[standup_plot_df["is_active"] == True][:-1]
                        .groupby("Moderator", as_index=False)
                        .count()
                    )
                    leaderboard_all_time_df.rename(
                        columns={"Date": "Number of Moderations"}, inplace=True
                    )
                    leaderboard_all_time_df["Colour"] = np.where(
                        leaderboard_all_time_df["Number of Moderations"]
                        == leaderboard_all_time_df["Number of Moderations"].max(),
                        "#FFB000",
                        "#072543",
                    )
                    domain = leaderboard_all_time_df["Moderator"].tolist()
                    range = leaderboard_all_time_df["Colour"].tolist()
                    chart_data = (
                        alt.Chart(leaderboard_all_time_df)
                        .mark_bar()
                        .encode(
                            x="Moderator",
                            y=alt.Y(
                                "Number of Moderations", axis=alt.Axis(tickMinStep=1)
                            ),
                            color=alt.Color(
                                "Moderator",
                                scale=alt.Scale(domain=domain, range=range),
                                legend=None,
                            ),
                        )
                    )
                    st.altair_chart(chart_data, use_container_width=True)

elif selectbox_page == "🪩 Retrospectives":
    moderators = moderators_df["moderator"][moderators_df["is_active"] == True].tolist()
    last_mod = retro_df["moderator"].iloc[-1]
    last_date = retro_df["date"].iloc[-1]
    today = dt.datetime.date(dt.datetime.today())

    # shut down tool on Saturdays and Sundays, otherwise set default next moderation date
    # default next moderation date will default to next Monday, Wednesday, or Friday, whichever is closest
    if today.isoweekday() == 6:
        st.markdown(
            "<p style='text-align: center; font-size: 50px; color: #072543'><b>Tool is under contract, and Saturdays are off!</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 75px'><b>🛌</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 25px; color: #FFB000'><b>Next Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
    elif today.isoweekday() == 7:
        st.markdown(
            "<p style='text-align: center; font-size: 50px; color: #072543'><b>Tool is under contract, and Sundays are off!</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 75px'><b>🛌",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 25px; color: #FFB000'><b>Next Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
    else:
        if today == last_date:
            top_label = "Today"
        else:
            top_label = f"{last_date} Retrospective"
        st.markdown(
            f"<p style='text-align: center; font-size: 25px; color: #FFB000'><b>{top_label}'s Moderator</b></p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='text-align: center; font-size: 50px; color: #072543'><b>{last_mod}</b></p>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([4, 1])
        with col1:
            available_team = st.multiselect(
                "Who is available to moderate?",
                moderators,
                moderators,
            )
        with col2:
            next_date = st.date_input("Next Retrospective's Date", last_date)

        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            button_next_mod = st.button(label="Get Lucky!")
        with col3:
            checkbox_save = st.checkbox("Save Results", True)

        st.write("")

        # if button is clicked, get the next moderator and show some stats
        if button_next_mod:
            # clear cache at the beginning of the instance
            st.cache_data.clear()

            # some fool proofing
            if len(available_team) < 1:
                st.markdown(
                    "<p style='text-align: center; font-size: 70px'><b>🤔</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align: center; font-size: 35px; color: #072543'><b>Select at least one team member!</b></p>",
                    unsafe_allow_html=True,
                )
            elif len(available_team) == 1:
                st.markdown(
                    "<p style='text-align: center; font-size: 35px; color: #072543'><b>There's only one team member available... Why did you even run this thing?</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p style='text-align: center; font-size: 70px'><b>🤨</b></p>",
                    unsafe_allow_html=True,
                )
            else:
                if last_date == next_date:
                    retro_df = retro_df[retro_df["date"] < next_date]
                    next_mod = get_next_mod(
                        retro_df["moderator"][::-1], available_team, 3
                    )
                    if checkbox_save:
                        retro_df = add_next_mod(retro_df, next_mod, next_date)
                        save_data = [
                            (moderators_df, "moderators"),
                            (standup_df, "standup_history"),
                            (retro_df, "retrospective_history"),
                        ]
                        upload_to_blob_storage(save_data, "moderators.xlsx")
                else:
                    next_mod = get_next_mod(
                        retro_df["moderator"][::-1], available_team, 3
                    )
                    if checkbox_save:
                        retro_df = add_next_mod(retro_df, next_mod, next_date)
                        save_data = [
                            (moderators_df, "moderators"),
                            (standup_df, "standup_history"),
                            (retro_df, "retrospective_history"),
                        ]
                        upload_to_blob_storage(save_data, "moderators.xlsx")

                st.markdown(
                    f"<p style='text-align: center; font-size: 25px; color: #FFB000'><b>{next_date} Retrospective's Moderator</b></p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='text-align: center; font-size: 75px; color: #072543'><b>{next_mod}</b></p>",
                    unsafe_allow_html=True,
                )

elif selectbox_page == "😎 Moderators":
    st.markdown(
        "<p style='text-align: center; font-size: 25px; color: #FFB000'><b>Moderators</b></p>",
        unsafe_allow_html=True,
    )
    description = "<p style='font-size: 16px; color: #072543'> <span style='font-size: 20px'><b>How To Use This Page</b></span>"
    description += "<br>– This page gives an overview of the current and previous members of the team"
    description += "<br>– It is best to select if a current team member is active or not rather than delete them, because this might affect the leaderboards"
    description += (
        "<br>– To <span style='color: #FFB000'><b>add</b></span> a new team member"
    )
    description += "<br>&emsp;&emsp; – Click on the <span style='color: #FFB000'><b>+</b></span> at the bottom row"
    description += "<br>&emsp;&emsp; – Type their name and check <span style='color: #FFB000'><b>isActive</b></span>"
    description += "<br>– To <span style='color: #FFB000'><b>remove</b></span> a team member (not recommended)"
    description += "<br>&emsp;&emsp; – Click on the <span style='color: #FFB000'><b>checkbox</b></span> in the leftmost column of their row"
    description += "<br>&emsp;&emsp; – Press <span style='color: #FFB000'><b>delete</b></span>/<span style='color: #FFB000'><b>backspace</b></span> on your keyboard"
    description += "<br>– Click on <span style='color: #FFB000'><b>Save</b></span>"
    description += "</p>"
    st.markdown(
        description,
        unsafe_allow_html=True,
    )
    edited_df = st.data_editor(
        moderators_df.rename(
            columns={"moderator": "Moderator", "is_active": "isActive"}
        ),
        num_rows="dynamic",
    )
    button_save = st.button("Save")
    if button_save:
        moderators_df = edited_df.rename(
            columns={"Moderator": "moderator", "isActive": "is_active"}
        )
        moderators_df.sort_values("moderator", inplace=True, ignore_index=True)
        save_data = [
            (moderators_df, "moderators"),
            (standup_df, "standup_history"),
            (retro_df, "retrospective_history"),
        ]
        upload_to_blob_storage(save_data, "moderators.xlsx")
        st.markdown(
            "<p style='text-align: center; font-size: 20px;'>🙌 Moderators have been saved! 🙌</p>",
            unsafe_allow_html=True,
        )
        st.cache_data.clear()
