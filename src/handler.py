from datetime import datetime
import os
import json
import logging
import boto3
import urllib3
from api.ncaa import (
    get_schools, get_schedule, get_scoreboard, get_game_details,
    get_wapit_players, get_wapit_stats, get_wapit_league, post_wapit_draft,
    get_all_wapit_stats, get_wapit_chat, post_wapit_chat, post_wapit_react,
    post_wapit_league, patch_wapit_league,           # ← new
    delete_wapit_team,        # ← new
    post_wapit_draft_bulk
)
from api.pick_poolr import (
    create_bet_record, get_bet_record, delete_bet_record, update_bet_record,
    check_bet_outcome, get_bets_for_year
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
        "/pick-poolr/bets": "get_bets_for_year",
        "/pick-poolr/bet": "get_bet_record",
        "/pick-poolr/bets/check-outcome": "check_bet_outcome",
    },
    "POST": {
        # HEALTH CHECK
        "/health": "post_health",

        # NCAA API
        "/ncaa/wapit/league": "post_wapit_draft",

        # PICK POOLR API
        "/pick-poolr/bet": "create_bet_record",
    },
    "PATCH": {
        # PICK POOLR API
        "/pick-poolr/bet": "update_bet_record",
    },
    "DELETE": {
        # PICK POOLR API
        "/pick-poolr/bet": "delete_bet_record"
    }
}

def match_route(event, logger):

    http_method = event["requestContext"]["http"]["method"]
    route_key = event["routeKey"]

    # For catch-all routes (ANY /{proxy+}), routeKey is "ANY /{proxy+}" — use actual request path instead
    if "/{proxy+}" in route_key:
        path = f"{http_method} {event['requestContext']['http']['path']}"
    else:
        path = route_key

    logger.info(f"HTTP Method: {http_method}, Route Key: {route_key}, Resolved Path: {path}")

    if http_method == "OPTIONS":
        return handle_options(event, logger)

    elif http_method == "GET":
        if path == "GET /health":
            # HEALTH CHECK
            return get_health(event, logger)

        # ESPN API
        elif path == "GET /espn/athletes":
            return get_athletes(event, logger)
        elif path == "GET /espn/teams":
            return get_teams(event, logger)
        elif path == "GET /espn/site/team":
            return get_site_team(event, logger)
        elif path == "GET /espn/core/team":
            return get_core_team(event, logger)
        elif path == "GET /espn/site/scoreboard":
            return get_site_scoreboard(event, logger)
        elif path == "GET /espn/cdn/scoreboard":
            return get_cdn_scoreboard(event, logger)
        elif path == "GET /espn/athlete":
            return get_athlete(event, logger)
        elif path == "GET /espn/cdn/schedule":
            return get_cdn_schedule(event, logger)
        elif path == "GET /espn/site/standings":
            return get_site_standings(event, logger)
        elif path == "GET /espn/cdn/standings":
            return get_cdn_standings(event, logger)
        elif path == "GET /espn/conference-standings":
            return get_conference_standings(event, logger)
        elif path == "GET /espn/team/roster":
            return get_team_roster(event, logger)
        elif path == "GET /espn/team/schedule":
            return get_team_schedule(event, logger)
        elif path == "GET /espn/team/injuries":
            return get_team_injuries(event, logger)
        elif path == "GET /espn/team/depth-chart":
            return get_team_depth_chart(event, logger)
        elif path == "GET /espn/athlete/overview":
            return get_athlete_overview(event, logger)
        elif path == "GET /espn/athlete/gamelog":
            return get_athlete_gamelog(event, logger)
        elif path == "GET /espn/athlete/eventlog":
            return get_athlete_eventlog(event, logger)
        elif path == "GET /espn/athlete/splits":
            return get_athlete_splits(event, logger)
        elif path == "GET /espn/game/summary":
            return get_game_summary(event, logger)
        elif path == "GET /espn/game/boxscore":
            return get_game_boxscore(event, logger)
        elif path == "GET /espn/game/playbyplay":
            return get_game_playbyplay(event, logger)
        elif path == "GET /espn/game/plays":
            return get_game_plays(event, logger)
        elif path == "GET /espn/game/drives":
            return get_game_drives(event, logger)
        elif path == "GET /espn/site/leaders":
            return get_site_leaders(event, logger)
        elif path == "GET /espn/core/leaders":
            return get_core_leaders(event, logger)
        elif path == "GET /espn/draft":
            return get_draft(event, logger)
        elif path == "GET /espn/team/news":
            return get_team_news(event, logger)
        elif path == "GET /espn/specific-nights":
            return get_specific_nights(event, logger)

        # NCAA API
        elif path == "GET /ncaa/schools":
            return get_schools(event, logger)
        elif path == "GET /ncaa/schedule":
            return get_schedule(event, logger)
        elif path == "GET /ncaa/scoreboard":
            return get_scoreboard(event, logger)
        elif path == "GET /ncaa/game":
            return get_game_details(event, logger)
        elif path == "GET /ncaa/wapit/players":
            return get_wapit_players(event, logger)
        elif path == "GET /ncaa/wapit/stats/player":
            return get_wapit_stats(event, logger)
        elif path == "GET /ncaa/wapit/stats/league":
            return get_all_wapit_stats(event, logger)
        elif path == "GET /ncaa/wapit/league/{league_id}/year/{year}":
            logger.info("GETTING WAPIT LEAGUE!!!")
            status_code, body = get_wapit_league(event, logger)
            return status_code, body
        elif path == "GET /ncaa/wapit/league/{league_id}/year/{year}/chat":
            status_code, body = get_wapit_chat(event, logger)
            return status_code, body

        # PICK POOLR API
        elif path == "GET /pick-poolr/bets":
            return get_bets_for_year(event, logger)
        elif path == "GET /pick-poolr/bet":
            return get_bet_record(event, logger)
        elif path == "GET /pick-poolr/bets/check-outcome":
            return check_bet_outcome(event, logger)

    elif http_method == "POST":
        # HEALTH CHECK
        if path == "POST /health":
            return post_health(event, logger)

        # NCAA API
        elif path == "POST /ncaa/wapit/league/{league_id}/year/{year}":
            return post_wapit_draft(event, logger)
        
        elif path == "POST /ncaa/wapit/league/{league_id}/year/{year}/chat":
            status_code, body = post_wapit_chat(event, logger)
            return status_code, body

        elif path == "POST /ncaa/wapit/league/{league_id}/year/{year}/chat/react":
            status_code, body = post_wapit_react(event, logger)
            return status_code, body
        
        elif path == "POST /ncaa/wapit/league":
            status_code, body = post_wapit_league(event, logger)
            return status_code, body
        
        # match_route POST block
        elif path == "POST /ncaa/wapit/league/{league_id}/year/{year}/draft/bulk":
            status_code, body = post_wapit_draft_bulk(event, logger)
            return status_code, body

        # PICK POOLR API
        elif path == "POST /pick-poolr/bet":
            return create_bet_record(event, logger)

    elif http_method == "PATCH":
        # PICK POOLR API
        if path == "PATCH /pick-poolr/bet":
            return update_bet_record(event, logger)
        
        elif path == "PATCH /ncaa/wapit/league/{league_id}/year/{year}":
            status_code, body = patch_wapit_league(event, logger)
            return status_code, body

    elif http_method == "DELETE":
        # PICK POOLR API
        if path == "DELETE /pick-poolr/bet":
            return delete_bet_record(event, logger)
        
        elif path == "DELETE /ncaa/wapit/league/{league_id}/year/{year}/pick":
            status_code, body = delete_wapit_last_pick(event, logger)
            return status_code, body

        elif path == "DELETE /ncaa/wapit/league/{league_id}/year/{year}/team":
            status_code, body = delete_wapit_team(event, logger)
            return status_code, body

    return return_404(event, logger)

def handler(event, context):
    logger.info("*** ENVIRONMENT VARIABLES ***")
    logger.info(os.environ['AWS_LAMBDA_LOG_GROUP_NAME'])
    logger.info(os.environ['AWS_LAMBDA_LOG_STREAM_NAME'])
    logger.info('*** EVENT ***')
    logger.info(event)
    logger.info("*** CONTEXT ***")
    logger.info(context)

    status_code = None
    response_body = {}

    try:
        # Route the request
        # Check if http_method is OPTIONS
        status_code, response_body = match_route(event, logger)

    except Exception as e:
        logger.exception("Exception caught in handler.py!!!")
        logger.exception(e)
        status_code, response_body = return_500(event, logger)

    return build_response(status_code, response_body)

def handle_options(event, logger):
    return 200, {
        "statusCode": "OK",
        "headers": {
            "Access-Control-Allow-Origin": "https://vsnandy.github.io,http://localhost:3000",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PATCH,DELETE",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps("Preflight Check Complete")
    }

def get_health(event, logger):
    return 200, {
        "status": "OK",
        "message": "Service is healthy",
        "timestamp": datetime.now().isoformat()
    }

def post_health(event, logger):
    return 201, {
        "status": "OK",
        "message": event.get("body", "No message received"),
        "timestamp": datetime.now().isoformat()
    }

def return_404(event, logger):
    return 404, {
        "status": "Not Found",
        "message": "Path does not exist",
        "timestamp": datetime.now().isoformat()
    }

def return_500(event, logger):
    return 500, {
        "status": "Internal Server Error",
        "message": "An exception occurred",
        "timestamp": datetime.now().isoformat()
    }