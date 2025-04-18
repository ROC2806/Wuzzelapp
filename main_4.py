import streamlit as st
import pandas as pd
import uuid
import random
import json
import os
from streamlit_option_menu import option_menu

# --- Dateipfad für die Speicherung ---
DATA_FILE = 'tournament_data.json'

# --- Funktion zum Laden und Speichern der Daten ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"tournaments": {}, "current_tournament": None}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# --- Seiten-Navigation ---
with st.sidebar:
    page = option_menu(
        "Wuzzel Turnier",
        ["Turnierverwaltung", "Teilnehmer", "Teams", "Spielplan", "Statistiken", "KO-Runde"],
        icons=["clipboard", "people", "trophy", "calendar", "bar-chart", "award"],
        menu_icon="cast",
        default_index=0
    )
st.title("Wuzzel Turnier Dashboard")

# --- Session State Setup ---
if "data" not in st.session_state:
    st.session_state.data = load_data()

# --- Helper Functions ---
def get_current(key):
    return st.session_state.data["tournaments"][st.session_state.data["current_tournament"]][key]

def set_current(key, value):
    st.session_state.data["tournaments"][st.session_state.data["current_tournament"]][key] = value

# --- Turnierverwaltung ---
if page == "Turnierverwaltung":
    st.header("Turnier erstellen oder auswählen")
    with st.form("create_tournament"):
        name = st.text_input("Name des Turniers")
        date = st.date_input("Datum des Turniers")
        is_group_phase = st.checkbox("Gruppenphase mit zwei Gruppen")
        submitted = st.form_submit_button("Neues Turnier erstellen")
        if submitted and name:
            st.session_state.data["tournaments"][name] = {
                "date": str(date),
                "players": [],
                "teams": [],
                "matches": [],
                "ko_round": [],
                "group_phase": is_group_phase,
                "groups": {"A": [], "B": []},
                "group_matches": {"A": [], "B": []}
            }
            st.session_state.data["current_tournament"] = name
            save_data(st.session_state.data)
            st.success(f"Turnier '{name}' erstellt und ausgewählt.")

    st.subheader("Existierende Turniere")
    if st.session_state.data["tournaments"]:
        selected = st.selectbox("Turnier auswählen", list(st.session_state.data["tournaments"].keys()))
        if st.button("Turnier laden"):
            st.session_state.data["current_tournament"] = selected
            save_data(st.session_state.data)
            st.success(f"Turnier '{selected}' geladen.")
    else:
        st.info("Noch keine Turniere vorhanden.")

if not st.session_state.data["current_tournament"]:
    st.stop()

# --- Teilnehmer ---
elif page == "Teilnehmer":
    st.header("Spieler hinzufügen")
    with st.form("add_player"):
        name = st.text_input("Name des Spielers")
        avatar = st.text_input("Avatar URL (optional)")
        submitted = st.form_submit_button("Hinzufügen")
        if submitted and name:
            get_current("players").append({"id": str(uuid.uuid4()), "name": name, "avatar": avatar})
            save_data(st.session_state.data)
            st.success(f"Spieler '{name}' wurde hinzugefügt.")

    st.subheader("Aktuelle Teilnehmer")
    for p in get_current("players"):
        st.markdown(f"- {p['name']}")

# --- Teams ---
elif page == "Teams":
    st.header("Teams erstellen")
    used_player_ids = [pid for team in get_current("teams") for pid in team['player_ids']]
    available_players = [p for p in get_current("players") if p['id'] not in used_player_ids]

    if len(available_players) < 2:
        st.warning("Mindestens 2 verfügbare Spieler erforderlich.")
    else:
        with st.form("create_team"):
            team_name = st.text_input("Teamname")
            player1 = st.selectbox("Spieler 1", available_players, format_func=lambda x: x['name'], key="p1_team")
            player2 = st.selectbox("Spieler 2", [p for p in available_players if p != player1], format_func=lambda x: x['name'], key="p2_team")
            create = st.form_submit_button("Team erstellen")
            if create and player1 != player2:
                get_current("teams").append({
                    "name": team_name,
                    "players": [player1['name'], player2['name']],
                    "player_ids": [player1['id'], player2['id']],
                    "points": 0,
                    "games_played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0
                })
                save_data(st.session_state.data)
                st.success(f"Team '{team_name}' erstellt.")

    st.subheader("Bestehende Teams")
    for t in get_current("teams"):
        st.markdown(f"- **{t['name']}** ({t['players'][0]} & {t['players'][1]})")

# --- Spielplan ---
elif page == "Spielplan":
    st.header("Spielplan")
    teams = get_current("teams")
    group_mode = get_current("group_phase")

    if len(teams) < 4:
        st.error("Mindestens 4 Teams erforderlich.")
    else:
        if group_mode and not get_current("group_matches")["A"] and not get_current("groups")["A"]:
            random.shuffle(teams)
            midpoint = len(teams) // 2
            set_current("groups", {"A": teams[:midpoint], "B": teams[midpoint:]})

            group_matches = {"A": [], "B": []}
            match_number = 1
            for group in ["A", "B"]:
                g_teams = get_current("groups")[group]
                for i in range(len(g_teams)):
                    for j in range(i+1, len(g_teams)):
                        for reverse in [False, True]:
                            t1 = g_teams[i if not reverse else j]["name"]
                            t2 = g_teams[j if not reverse else i]["name"]
                            group_matches[group].append({
                                "match_number": match_number,
                                "team1": t1, "team2": t2, "score": "-",
                                "color": f"{t1} (Rot) vs {t2} (Blau)"
                            })
                            match_number += 1
            set_current("group_matches", group_matches)

        elif not group_mode and not get_current("matches"):
            match_number = 1
            for i in range(len(teams)):
                for j in range(i+1, len(teams)):
                    for reverse in [False, True]:
                        t1 = teams[i if not reverse else j]["name"]
                        t2 = teams[j if not reverse else i]["name"]
                        get_current("matches").append({
                            "match_number": match_number,
                            "team1": t1, "team2": t2, "score": "-",
                            "color": f"{t1} (Rot) vs {t2} (Blau)"
                        })
                        match_number += 1
            save_data(st.session_state.data)

        if group_mode:
            for group in ["A", "B"]:
                st.subheader(f"Gruppe {group}")
                for idx, match in enumerate(get_current("group_matches")[group]):
                    score = st.text_input(f"{match['match_number']}. {match['team1']} vs {match['team2']}",
                                          value=match['score'], key=f"group_{group}_{idx}")
                    match['score'] = score
            save_data(st.session_state.data)
        else:
            st.subheader("Spiele & Ergebnisse")
            for idx, match in enumerate(get_current("matches")):
                score = st.text_input(f"{match['match_number']}. {match['team1']} vs {match['team2']} ({match['color']})",
                                      value=match['score'], key=f"match_{idx}")
                match['score'] = score
            save_data(st.session_state.data)

# --- Statistiken ---
elif page == "Statistiken":
    st.header("Ergebnis-Tabelle")
    teams = get_current("teams")
    group_mode = get_current("group_phase")

    def update_stats(teams, matches):
        # Reset stats
        for team in teams:
            team.update({
                "points": 0,
                "games_played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0
            })

        team_lookup = {team["name"]: team for team in teams}

        for match in matches:
            score = match["score"]
            if score != "-" and ":" in score:
                try:
                    s1, s2 = map(int, score.strip().split(":"))
                    t1 = team_lookup.get(match["team1"])
                    t2 = team_lookup.get(match["team2"])
                    if not t1 or not t2:
                        continue

                    t1["games_played"] += 1
                    t2["games_played"] += 1

                    t1["goals_for"] += s1
                    t1["goals_against"] += s2

                    t2["goals_for"] += s2
                    t2["goals_against"] += s1

                    if s1 > s2:
                        t1["points"] += 3
                        t1["wins"] += 1
                        t2["losses"] += 1
                    elif s2 > s1:
                        t2["points"] += 3
                        t2["wins"] += 1
                        t1["losses"] += 1
                    else:
                        t1["points"] += 1
                        t2["points"] += 1
                        t1["draws"] += 1
                        t2["draws"] += 1
                except:
                    continue

    def render_table(df):
        df["Tordifferenz"] = df["goals_for"] - df["goals_against"]
        df["Spiele"] = df["games_played"]
        df["S"] = df["wins"]
        df["U"] = df["draws"]
        df["N"] = df["losses"]
        df["Torverhältnis"] = df.apply(lambda row: f"{row['goals_for']}:{row['goals_against']} ({row['Tordifferenz']:+})", axis=1)
        df = df.sort_values(by=["points", "Tordifferenz", "goals_for"], ascending=False).reset_index(drop=True)
        df["Rang"] = df.index + 1

        df_display = df[[
            "Rang", "name", "Spiele", "S", "U", "N", "Torverhältnis", "points"
        ]].rename(columns={
            "name": "Team", "points": "Punkte"
        })

        st.dataframe(df_display.style.format(precision=0)
            .set_properties(**{"font-size": "16px", "border-color": "black"})
            .set_table_styles([
                {"selector": "tbody tr:nth-child(even)", "props": [("background-color", "#f2f2f2")]},
                {"selector": "th", "props": [("background-color", "#e0e0e0"), ("font-weight", "bold")]}
            ]), use_container_width=True)

    if group_mode:
        for group in ["A", "B"]:
            group_teams = get_current("groups")[group]
            group_matches = get_current("group_matches")[group]
            update_stats(group_teams, group_matches)
            st.subheader(f"Gruppe {group}")
            render_table(pd.DataFrame(group_teams))
    else:
        matches = get_current("matches")
        update_stats(teams, matches)
        render_table(pd.DataFrame(teams))

# --- KO-Runde ---
elif page == "KO-Runde":
    st.header("KO-Runde")
    teams = get_current("teams")
    if len(teams) < 4:
        st.error("Mindestens 4 Teams erforderlich.")
    else:
        group_mode = get_current("group_phase")
        if st.button("KO-Runde generieren"):
            df = pd.DataFrame(teams)
            if group_mode:
                group_stats = {}
                for group in ["A", "B"]:
                    g_teams = get_current("groups")[group]
                    g_df = pd.DataFrame(g_teams)
                    g_df["Tordifferenz"] = g_df["goals_for"] - g_df["goals_against"]
                    g_df = g_df.sort_values(by=["points", "Tordifferenz", "goals_for"], ascending=False)
                    group_stats[group] = g_df.head(2)
                top4 = [
                    {"round": "Halbfinale 1", "team1": group_stats["A"].iloc[0]["name"], "team2": group_stats["B"].iloc[1]["name"], "score": "-"},
                    {"round": "Halbfinale 2", "team1": group_stats["B"].iloc[0]["name"], "team2": group_stats["A"].iloc[1]["name"], "score": "-"}
                ]
            else:
                top4_df = df.sort_values(by=["points", "goals_for"], ascending=False).head(4)
                top4 = [
                    {"round": "Halbfinale 1", "team1": top4_df.iloc[0]["name"], "team2": top4_df.iloc[3]["name"], "score": "-"},
                    {"round": "Halbfinale 2", "team1": top4_df.iloc[1]["name"], "team2": top4_df.iloc[2]["name"], "score": "-"}
                ]
            set_current("ko_round", top4)
            save_data(st.session_state.data)
            st.success("KO-Runde erstellt!")

    winners = []
    losers = []  # Liste für die Verlierer der Halbfinals (für das Spiel um Platz 3)
    for idx, match in enumerate(get_current("ko_round")):
        score = st.text_input(f"{match['round']}: {match['team1']} vs {match['team2']}", value=match['score'], key=f"ko_{idx}")
        match['score'] = score
        if score != "-" and ":" in score:
            try:
                s1, s2 = map(int, score.split(":"))
                if s1 > s2:
                    winners.append(match['team1'])
                    losers.append(match['team2'])
                elif s2 > s1:
                    winners.append(match['team2'])
                    losers.append(match['team1'])
            except:
                pass

    if len(winners) == 2:
        # Spiel um Platz 3
        st.subheader("Spiel um Platz 3")
        third_place_score = st.text_input(f"Spiel um Platz 3: {losers[0]} vs {losers[1]}", key="third_place")
        if third_place_score != "-" and ":" in third_place_score:
            try:
                tps1, tps2 = map(int, third_place_score.split(":"))
                if tps1 > tps2:
                    st.success(f"3. Platz: {losers[0]}")
                    third_place = losers[0]
                elif tps2 > tps1:
                    st.success(f"3. Platz: {losers[1]}")
                    third_place = losers[1]
                else:
                    st.warning("Unentschieden im Spiel um Platz 3!")
            except:
                st.error("Ungültiges Ergebnisformat.")

        # Finale
        st.subheader("Finale")
        final_score = st.text_input(f"Finale: {winners[0]} vs {winners[1]}", key="final")
        if final_score != "-" and ":" in final_score:
            try:
                fs1, fs2 = map(int, final_score.split(":"))
                if fs1 > fs2:
                    st.success(f"Turniersieger: {winners[0]}")
                    winner = winners[0]
                    runner_up = winners[1]
                elif fs2 > fs1:
                    st.success(f"Turniersieger: {winners[1]}")
                    winner = winners[1]
                    runner_up = winners[0]
                else:
                    st.warning("Unentschieden im Finale!")
            except:
                st.error("Ungültiges Ergebnisformat.")

        # Ergebnisse speichern
        if 'winner' in locals() and 'runner_up' in locals() and 'third_place' in locals():
            rankings = {
                "1. Platz": winner,
                "2. Platz": runner_up,
                "3. Platz": third_place
            }
            st.subheader("Platzierungen")
            rankings_df = pd.DataFrame(list(rankings.items()), columns=["Platz", "Team"])
            st.table(rankings_df)
            
            # Platzierungen im Session-State speichern
            st.session_state.rankings = rankings
            save_data(st.session_state.data)
            st.success("Platzierungen wurden gespeichert!")



