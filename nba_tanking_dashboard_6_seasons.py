
# nba_tanking_dashboard_fixed_score.py

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="NBA Tanking Analysis Dashboard",
    layout="wide"
)

st.title("NBA Post-All-Star Tanking Analysis")
st.write(
    """
    This dashboard ranks possible tanking behavior after the All-Star break.
    The fixed score only ranks teams that were below .500 before the All-Star break.
    This prevents strong playoff teams from being mislabeled as tanking teams.
    """
)

@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    df.columns = [c.strip() for c in df.columns]
    return df

DATA_FILE = "nba_final_tanking_dataset_fixed_6_seasons.csv"

try:
    df = load_data(DATA_FILE)
except FileNotFoundError:
    st.error(
        f"Could not find {DATA_FILE}. Run merge_tanking_project_fixed.py first, then put this dashboard in the same folder as the CSV."
    )
    st.stop()

def has_cols(data, cols):
    return all(col in data.columns for col in cols)

# Bubble size must be positive
if "tanking_score" in df.columns:
    df["bubble_size"] = df["raw_tanking_score"].abs() + 1 if "raw_tanking_score" in df.columns else df["tanking_score"].abs() + 1

st.sidebar.header("Filters")

if "season" in df.columns:
    seasons = sorted(df["season"].dropna().unique())
    selected_seasons = st.sidebar.multiselect(
        "Select season(s)",
        seasons,
        default=seasons
    )
    df = df[df["season"].isin(selected_seasons)]

if "TEAM_NAME" in df.columns:
    teams = sorted(df["TEAM_NAME"].dropna().unique())
    selected_teams = st.sidebar.multiselect(
        "Select team(s)",
        teams,
        default=teams
    )
    df = df[df["TEAM_NAME"].isin(selected_teams)]

candidate_filter = st.sidebar.radio(
    "Team type",
    ["All teams", "Only tank candidates", "Only playoff/above-.500 teams"]
)

if "lottery_candidate" in df.columns:
    if candidate_filter == "Only tank candidates":
        df = df[df["lottery_candidate"] == True]
    elif candidate_filter == "Only playoff/above-.500 teams":
        df = df[df["lottery_candidate"] == False]

st.subheader("Project Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Teams", df["TEAM_NAME"].nunique() if "TEAM_NAME" in df.columns else len(df))

with col2:
    st.metric("Seasons", df["season"].nunique() if "season" in df.columns else "N/A")

with col3:
    if "tanking_score" in df.columns:
        st.metric("Avg Adjusted Tanking Score", round(df["tanking_score"].mean(), 2))
    else:
        st.metric("Avg Adjusted Tanking Score", "N/A")

with col4:
    if "raw_tanking_score" in df.columns:
        st.metric("Avg Raw Score", round(df["raw_tanking_score"].mean(), 2))
    else:
        st.metric("Avg Raw Score", "N/A")

st.info(
    """
    Adjusted tanking score = raw tanking score only for teams below .500 before the All-Star break.
    Above-.500 teams get a tanking score of 0 because they usually have playoff-rest incentives, not tanking incentives.
    """
)

st.subheader("Methodology")

st.write(
    """
    A team is treated as a tank candidate only if it was below .500 before the All-Star break.
    The adjusted tanking score combines four signals: win projection drop, starter minutes drop,
    increase in players used, and increase in lineup experimentation. Playoff-level teams are
    given a score of 0 to avoid confusing playoff rest with tanking.
    """
)


st.subheader("Top Adjusted Tanking Score Teams")

if "tanking_score" in df.columns:
    display_cols = [
        col for col in [
            "season",
            "TEAM_ABBREVIATION",
            "TEAM_NAME",
            "win_pct_pre_asg",
            "projection_difference",
            "starter_minutes_change_per_game",
            "players_used_change",
            "lineups_used_change",
            "raw_tanking_score",
            "tanking_score",
            "score_note"
        ]
        if col in df.columns
    ]

    top_n = st.slider("Number of teams to show", min_value=5, max_value=30, value=15)

    top_tankers = df.sort_values("tanking_score", ascending=False).head(top_n)

    st.dataframe(top_tankers[display_cols], use_container_width=True)

    if has_cols(df, ["TEAM_NAME", "season", "tanking_score"]):
        chart_df = top_tankers.copy()
        chart_df["team_season"] = chart_df["season"].astype(str) + " " + chart_df["TEAM_NAME"].astype(str)

        fig = px.bar(
            chart_df.sort_values("tanking_score"),
            x="tanking_score",
            y="team_season",
            orientation="h",
            title="Top Adjusted Tanking Score Teams",
            labels={
                "tanking_score": "Adjusted Tanking Score",
                "team_season": "Team Season"
            }
        )

        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Column `tanking_score` was not found.")


st.subheader("Tanking Score Breakdown")

breakdown_cols = [
    "TEAM_NAME",
    "season",
    "win_projection_drop",
    "starter_minutes_drop",
    "players_used_increase",
    "lineup_experimentation_increase",
    "tanking_score"
]

if all(col in df.columns for col in breakdown_cols):

    breakdown_df = (
        df[df["tanking_score"] > 0]
        .sort_values("tanking_score", ascending=False)
        .head(15)
    )

    st.dataframe(
        breakdown_df[breakdown_cols],
        use_container_width=True
    )

    breakdown_long = breakdown_df.melt(
        id_vars=["TEAM_NAME", "season"],
        value_vars=[
            "win_projection_drop",
            "starter_minutes_drop",
            "players_used_increase",
            "lineup_experimentation_increase"
        ],
        var_name="Score Component",
        value_name="Value"
    )

    breakdown_long["team_season"] = (
        breakdown_long["season"].astype(str)
        + " "
        + breakdown_long["TEAM_NAME"].astype(str)
    )

    fig = px.bar(
        breakdown_long,
        x="Value",
        y="team_season",
        color="Score Component",
        orientation="h",
        title="What Created Each Team's Tanking Score?"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("This section needs the tanking score component columns.")

st.subheader("Raw Score vs Adjusted Score")

if has_cols(df, ["raw_tanking_score", "tanking_score", "TEAM_NAME"]):
    fig = px.scatter(
        df,
        x="raw_tanking_score",
        y="tanking_score",
        color="lottery_candidate" if "lottery_candidate" in df.columns else None,
        hover_name="TEAM_NAME",
        hover_data=[
            col for col in [
                "season",
                "TEAM_ABBREVIATION",
                "win_pct_pre_asg",
                "projection_difference",
                "score_note"
            ]
            if col in df.columns
        ],
        title="Raw Score vs Adjusted Tanking Score",
        labels={
            "raw_tanking_score": "Raw Score",
            "tanking_score": "Adjusted Tanking Score"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

st.subheader("Projected Wins vs Actual Wins")

if has_cols(df, ["projected_wins_before_asg", "actual_wins", "TEAM_NAME"]):
    fig = px.scatter(
        df,
        x="projected_wins_before_asg",
        y="actual_wins",
        color="season" if "season" in df.columns else None,
        hover_name="TEAM_NAME",
        hover_data=[
            col for col in [
                "TEAM_ABBREVIATION",
                "projection_difference",
                "tanking_score",
                "raw_tanking_score",
                "lottery_candidate"
            ]
            if col in df.columns
        ],
        title="Pre-All-Star Projected Wins vs Actual Wins",
        labels={
            "projected_wins_before_asg": "Projected Wins Before ASG",
            "actual_wins": "Actual Wins"
        }
    )

    x_min = df["projected_wins_before_asg"].min()
    x_max = df["projected_wins_before_asg"].max()

    fig.add_shape(
        type="line",
        x0=x_min,
        y0=x_min,
        x1=x_max,
        y1=x_max,
        line=dict(dash="dash")
    )

    st.plotly_chart(fig, use_container_width=True)

st.subheader("Post-All-Star Behavior Changes")

left, right = st.columns(2)

with left:
    if has_cols(df, ["starter_minutes_change_per_game", "TEAM_NAME", "season"]):
        temp = df.sort_values("starter_minutes_change_per_game").head(20).copy()
        temp["team_season"] = temp["season"].astype(str) + " " + temp["TEAM_NAME"].astype(str)

        fig = px.bar(
            temp.sort_values("starter_minutes_change_per_game"),
            x="starter_minutes_change_per_game",
            y="team_season",
            orientation="h",
            title="Biggest Starter Minutes Drops After ASG",
            labels={
                "starter_minutes_change_per_game": "Starter Minutes Change Per Game",
                "team_season": "Team Season"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

with right:
    if has_cols(df, ["lineups_used_change", "TEAM_NAME", "season"]):
        temp = df.sort_values("lineups_used_change", ascending=False).head(20).copy()
        temp["team_season"] = temp["season"].astype(str) + " " + temp["TEAM_NAME"].astype(str)

        fig = px.bar(
            temp.sort_values("lineups_used_change"),
            x="lineups_used_change",
            y="team_season",
            orientation="h",
            title="Biggest Lineup Experimentation Increases After ASG",
            labels={
                "lineups_used_change": "Lineups Used Change",
                "team_season": "Team Season"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

st.subheader("Lineup Volatility vs Winning Drop")

if has_cols(df, ["lineups_used_change", "projection_difference", "TEAM_NAME"]):
    fig = px.scatter(
        df,
        x="lineups_used_change",
        y="projection_difference",
        color="lottery_candidate" if "lottery_candidate" in df.columns else None,
        size="bubble_size" if "bubble_size" in df.columns else None,
        hover_name="TEAM_NAME",
        hover_data=[
            col for col in [
                "season",
                "TEAM_ABBREVIATION",
                "starter_minutes_change_per_game",
                "players_used_change",
                "raw_tanking_score",
                "tanking_score"
            ]
            if col in df.columns
        ],
        title="Lineup Change vs Projection Difference",
        labels={
            "lineups_used_change": "Lineups Used Change After ASG",
            "projection_difference": "Actual Wins - Projected Wins"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

st.subheader("Team Detail")

if "TEAM_NAME" in df.columns:
    selected_team = st.selectbox("Choose a team", sorted(df["TEAM_NAME"].dropna().unique()))

    team_df = df[df["TEAM_NAME"] == selected_team].copy()

    detail_cols = [
        col for col in [
            "season",
            "TEAM_ABBREVIATION",
            "TEAM_NAME",
            "win_pct_pre_asg",
            "projected_wins_before_asg",
            "actual_wins",
            "projection_difference",
            "starter_minutes_change_per_game",
            "players_used_change",
            "lineups_used_change",
            "raw_tanking_score",
            "lottery_candidate",
            "tanking_score",
            "score_note"
        ]
        if col in team_df.columns
    ]

    st.dataframe(team_df[detail_cols], use_container_width=True)

    if has_cols(team_df, ["season", "tanking_score"]):
        fig = px.line(
            team_df.sort_values("season"),
            x="season",
            y="tanking_score",
            markers=True,
            title=f"{selected_team} Adjusted Tanking Score by Season",
            labels={
                "season": "Season",
                "tanking_score": "Adjusted Tanking Score"
            }
        )

        st.plotly_chart(fig, use_container_width=True)



st.subheader("Average Tanking Score by Season")

if "season" in df.columns and "tanking_score" in df.columns:

    season_summary = (
        df.groupby("season")
        .agg(
            avg_tanking_score=("tanking_score", "mean"),
            median_tanking_score=("tanking_score", "median"),
            max_tanking_score=("tanking_score", "max"),
            teams=("TEAM_NAME", "nunique")
        )
        .reset_index()
        .sort_values("avg_tanking_score", ascending=False)
    )

    highest_year = season_summary.iloc[0]
    lowest_year = season_summary.iloc[-1]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Highest Avg Tanking Score Season",
            highest_year["season"],
            round(highest_year["avg_tanking_score"], 2)
        )

    with col2:
        st.metric(
            "Lowest Avg Tanking Score Season",
            lowest_year["season"],
            round(lowest_year["avg_tanking_score"], 2)
        )

    st.dataframe(
        season_summary,
        use_container_width=True
    )

    fig = px.bar(
        season_summary.sort_values("season"),
        x="season",
        y="avg_tanking_score",
        title="Average Adjusted Tanking Score by Season",
        labels={
            "season": "Season",
            "avg_tanking_score": "Average Tanking Score"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("This section needs `season` and `tanking_score` columns.")
    
    
    
    
    
st.subheader("Team That Tanked the Most Across 6 Seasons")

if "TEAM_NAME" in df.columns and "tanking_score" in df.columns:

    team_5yr_summary = (
        df.groupby(["TEAM_ABBREVIATION", "TEAM_NAME"])
        .agg(
            total_tanking_score=("tanking_score", "sum"),
            avg_tanking_score=("tanking_score", "mean"),
            max_single_season_score=("tanking_score", "max"),
            tank_candidate_seasons=("lottery_candidate", "sum"),
            seasons_tracked=("season", "nunique")
        )
        .reset_index()
        .sort_values("total_tanking_score", ascending=False)
    )

    top_team = team_5yr_summary.iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Most Tanking Across 5 Seasons",
            top_team["TEAM_NAME"],
            round(top_team["total_tanking_score"], 2)
        )

    with col2:
        st.metric(
            "Average Tanking Score",
            round(top_team["avg_tanking_score"], 2)
        )

    with col3:
        st.metric(
            "Tank Candidate Seasons",
            int(top_team["tank_candidate_seasons"])
        )

    st.dataframe(
        team_5yr_summary,
        use_container_width=True
    )

    fig = px.bar(
        team_5yr_summary.head(15).sort_values("total_tanking_score"),
        x="total_tanking_score",
        y="TEAM_NAME",
        orientation="h",
        title="Highest Total Tanking Score Across 6 Seasons",
        labels={
            "total_tanking_score": "Total Tanking Score",
            "TEAM_NAME": "Team"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("This section needs `TEAM_NAME` and `tanking_score` columns.")



st.subheader("Raw Data / Download")

with st.expander("View Raw Data"):
    st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered Data as CSV",
    data=csv,
    file_name="filtered_nba_tanking_data_fixed.csv",
    mime="text/csv"
)






st.subheader("Did Top Tanking Teams Get a Top-4 Pick?")

top4_next_draft = {
    "2020-21": ["DET", "HOU", "CLE", "TOR"],
    "2021-22": ["ORL", "OKC", "HOU", "SAC"],
    "2022-23": ["SAS", "CHA", "POR", "HOU"],
    "2023-24": ["ATL", "WAS", "HOU", "SAS"],
    "2024-25": ["DAL", "SAS", "PHI", "CHA"],
    "2025-26": ["WAS", "UTA", "MEM", "CHI"]
}

if "season" in df.columns and "TEAM_ABBREVIATION" in df.columns and "tanking_score" in df.columns:

    draft_df = df.copy()

    draft_df["got_top4_pick_next_draft"] = draft_df.apply(
        lambda row: row["TEAM_ABBREVIATION"] in top4_next_draft.get(row["season"], []),
        axis=1
    )

    top_n_draft = st.slider(
        "Top tanking teams to check",
        min_value=5,
        max_value=30,
        value=15
    )

    top_tanking_draft = (
        draft_df[draft_df["tanking_score"] > 0]
        .sort_values("tanking_score", ascending=False)
        .head(top_n_draft)
    )
    

    top4_count = top_tanking_draft["got_top4_pick_next_draft"].sum()
    top4_rate = top4_count / top_n_draft

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Top Tanking Teams With Top-4 Pick",
            f"{top4_count} out of {top_n_draft}"
        )

    with col2:
        st.metric(
            "Top-4 Pick Rate",
            f"{top4_rate:.1%}"
        )

    show_cols = [
        col for col in [
            "season",
            "TEAM_ABBREVIATION",
            "TEAM_NAME",
            "tanking_score",
            "got_top4_pick_next_draft"
        ]
        if col in top_tanking_draft.columns
    ]

    st.dataframe(
        top_tanking_draft[show_cols],
        use_container_width=True
    )

    fig = px.bar(
        top_tanking_draft,
        x="TEAM_NAME",
        y="tanking_score",
        color="got_top4_pick_next_draft",
        title="Top Tanking Teams and Whether They Got a Top-4 Pick",
        labels={
            "TEAM_NAME": "Team",
            "tanking_score": "Adjusted Tanking Score",
            "got_top4_pick_next_draft": "Got Top-4 Pick"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("This section needs season, TEAM_ABBREVIATION, and tanking_score columns.")

