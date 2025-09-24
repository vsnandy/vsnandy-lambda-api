from datetime import datetime
import os
import json
import logging
import boto3
import urllib3
from api.ncaa import (
    get_schools, get_schedule, get_scoreboard, get_game_details, 
    get_wapit_players, get_wapit_stats, get_wapit_league, post_wapit_draft, 
    get_all_wapit_stats
)
from api.pick_poolr import (
    create_bet_record, get_bet_record, delete_bet_record, update_bet_record,
    check_bet_outcome
)
from api.espn import (
    get_athletes, get_teams, get_site_team, get_core_team, get_site_scoreboard, 
    get_cdn_scoreboard, get_athlete, get_cdn_schedule, get_site_standings,
    get_cdn_standings, get_conference_standings, get_team_roster,
    get_team_schedule, get_team_injuries, get_team_depth_chart, get_athlete_overview,
    get_athlete_gamelog, get_athlete_eventlog, get_athlete_splits,
    get_game_summary, get_game_boxscore, get_game_playbyplay, get_game_plays,
    get_game_drives, get_site_leaders, get_core_leaders, get_draft,
    get_team_news, get_specific_nights
)
from utils.helper import build_response

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


dynamodb = boto3.resource("dynamodb")

# Define routes
ROUTES = {
    "OPTIONS": {
        "default": "handle_options"
    },
    "GET": {
        # HEALTH CHECK
        "/health": "get_health",

        # ESPN API
        "/espn/athletes": "get_athletes",
        "/espn/teams": "get_teams",
        "/espn/site/team": "get_site_team",
        "/espn/core/team": "get_core_team",
        "/espn/site/scoreboard": "get_site_scoreboard",
        "/espn/cdn/scoreboard": "get_cdn_scoreboard",
        "/espn/athlete": "get_athlete",
        "/espn/cdn/schedule": "get_cdn_schedule",
        "/espn/site/standings": "get_site_standings",
        "/espn/cdn/standings": "get_cdn_standings",
        "/espn/conference-standings": "get_conference_standings",
        "/espn/team/roster": "get_team_roster",
        "/espn/team/schedule": "get_team_schedule",
        "/espn/team/injuries": "get_team_injuries",
        "/espn/team/depth-chart": "get_team_depth_chart",
        "/espn/athlete/overview": "get_athlete_overview",
        "/espn/athlete/gamelog": "get_athlete_gamelog",
        "/espn/athlete/eventlog": "get_athlete_eventlog",
        "/espn/athlete/splits": "get_athlete_splits",
        "/espn/game/summary": "get_game_summary",
        "/espn/game/boxscore": "get_game_boxscore",
        "/espn/game/playbyplay": "get_game_playbyplay",
        "/espn/game/plays": "get_game_plays",
        "/espn/game/drives": "get_game_drives",
        "/espn/site/leaders": "get_site_leaders",
        "/espn/core/leaders": "get_core_leaders",
        "/espn/draft": "get_draft",
        "/espn/team/news": "get_team_news",
        "/espn/specific-nights": "get_specific_nights",

        # NCAA API
        "/ncaa/schools": "get_schools",
        "/ncaa/schedule": "get_schedule",
        "/ncaa/scoreboard": "get_scoreboard",
        "/ncaa/game": "get_game_details",
        "/ncaa/wapit/players": "get_wapit_players",
        "/ncaa/wapit/stats/player": "get_wapit_stats",
        "/ncaa/wapit/stats/league": "get_all_wapit_stats",
        "/ncaa/wapit/league": "get_wapit_league",

        # PICK POOLR API
        "/pick-poolr/bets": "get_bet_record",
        "/pick-poolr/bets/check-outcome": "check_bet_outcome",
    },
    "POST": {
        # HEALTH CHECK
        "/health": "post_health",

        # NCAA API
        "/ncaa/wapit/league": "post_wapit_draft",

        # PICK POOLR API
        "/pick-poolr/bets": "create_bet_record",
    },
    "PATCH": {
        # PICK POOLR API
        "/pick-poolr/bets": "update_bet_record",
    },
    "DELETE": {
        # PICK POOLR API
        "/pick-poolr/bets": "delete_bet_record"
    }
}

def handler(event, context):
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')
    logger.info(event)

    http_method = event["requestContext"]["http"]["method"]
    path = event["requestContext"]["http"]["path"]

    logger.info(f"HTTP Method: {http_method}, Path: {path}")

    status_code = 200
    response_body = {}

    try:
        # Route the request
        # Check if http_method is OPTIONS
        if (http_method.equals("OPTIONS")):
            route_handler = ROUTES["OPTIONS"]["default"]
        else:
            route_handler = ROUTES.get(http_method, {}).get(path, None)
        logger.info(f"Route Handler: {route_handler}")
        if route_handler:
            handler_function = globals()[route_handler]
            response_body = handler_function(event, logger)
        else:
            return build_response(404, "Not Found")

    except Exception as e:
        logger.exception("Exception caught in handler.py!!!")
        logger.exception(e)
        return build_response(500, "Server Error")

    return build_response(status_code, response_body)

def handle_options(event, logger):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PATCH,DELETE",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps("Preflight Check Complete")
    }

def get_health(event, logger):
    return {
        "status": "OK",
        "message": "Service is healthy",
        "timestamp": datetime.now().isoformat()
    }

def post_health(event, logger):
    return {
        "status": "OK",
        "message": event.get("body", "No message received"),
        "timestamp": datetime.now().isoformat()
    }