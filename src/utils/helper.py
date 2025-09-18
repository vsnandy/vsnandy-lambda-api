import json

from datetime import datetime, timedelta
from itertools import groupby

####################
# HELPER FUNCTIONS #
####################

# Build the response to send
def build_response(status_code, response_body=None):
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,DELETE,PATCH",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        }
    }

    if response_body is not None:
        response["body"] = response_body if isinstance(response_body, str) else json.dumps(response_body, default=str)
    return response

# Calculate the nth day of week of the month/year
def get_nth_day(year, month, day, n):
    # Get first day of month
    date = datetime(year, month, 1)
    dow = date.isoweekday()
    # ISO Weekday is 1 = Monday, 7 = Sunday

    while(dow != day):
        date = date + timedelta(days=1)
        dow = date.isoweekday()

    # Found the 1st day in the given month/year
    # Add (n-1)*7 more days to get the nth day in the given month/year
    date = date + timedelta(days=(n-1)*7)

    return date

# Get users in a cognito user group
# Will be used to get all the league members/teams
def get_users_in_group(cognito, user_pool_id, group_name, logger):
    logger.info("Getting cognito users for User Pool ID - " + user_pool_id)
    users = []
    
    response = cognito.list_users_in_group(
        UserPoolId=user_pool_id,
        GroupName=group_name,
        Limit=60
    )

    logger.info("get_users_in_group response: ")
    logger.info(response)

    users.extend(response["Users"])

    return users


# Given a draft, populate the list of teams
def populate_teams_in_league(draft, logger):
    logger.info("Populating teams for League --- " + draft[0]["LeagueID"])

    '''
    Example draft_picks structure
        draft_picks = [
            {"LeagueID": "NBA2024", "PickNumber": 1, "TeamID": "TeamA", "PlayerID": "123", "PlayerName": "LeBron James", "Position": "SF"},
            {"LeagueID": "NBA2024", "PickNumber": 2, "TeamID": "TeamB", "PlayerID": "456", "PlayerName": "Giannis Antetokounmpo", "Position": "PF"},
            {"LeagueID": "NBA2024", "PickNumber": 3, "TeamID": "TeamC", "PlayerID": "789", "PlayerName": "Luka Dončić", "Position": "PG"},
            {"LeagueID": "NBA2024", "PickNumber": 4, "TeamID": "TeamD", "PlayerID": "101", "PlayerName": "Nikola Jokić", "Position": "C"},
            {"LeagueID": "NBA2024", "PickNumber": 5, "TeamID": "TeamE", "PlayerID": "112", "PlayerName": "Kevin Durant", "Position": "SF"},
        ]
    '''
    
    # Sort first
    picks_sorted = sorted(draft, key=lambda x: x["TeamID"])

    # Group by team
    teams = { key: list(group) for key, group in groupby(picks_sorted, key=lambda x: x["TeamID"]) }

    return teams