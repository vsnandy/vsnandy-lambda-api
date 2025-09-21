import json
import urllib3

ESPN_SPORTS_URL = "https://sports.core.api.espn.com"
ESPN_SITE_WEB_URL = "https://site.web.api.espn.com"
ESPN_SITE_URL = "https://site.api.espn.com"
ESPN_CDN_URL = "https://cdn.espn.com"

http = urllib3.PoolManager()

# Get All Players for Sport
# GET /espn/athletes?sport=:sport&league=:league&limit=:limit&page=:page
def get_athletes(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        limit = event.get("queryStringParameters", {}).get("limit", 100)
        page = event.get("queryStringParameters", {}).get("page", 1)
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400
        
        response = http.request("GET", f"{ESPN_SPORTS_URL}/v3/sports/{sport}/{league}/athletes?limit={limit}&page={page}")
        print("Response Code:", response.status)

        data = json.loads(response.data)

        print("Response Keys:", data.keys())
        print("Response Pages:", data["pageCount"])

        body = {
            "players": data["items"],
            "pageCount": data["pageCount"],
            "count": data["count"],
            "pageIndex": data["pageIndex"],
            "pageSize": data["pageSize"]
        }

        return body
    except Exception as e:
        logger.exception("Exception in Get All Players Method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get all teams for sport
# GET /espn/teams
def get_teams(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams",
        )

        print("Response Code:", response.status)
        data = json.loads(response.data)
        body = {
            "teams": data["sports"][0]["leagues"][0]["teams"]
        }
        return body

    except Exception as e:
        logger.exception("Exception in Get Teams method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team (SITE API)
# GET /espn/site/team?sport=:sport&league=:league&id=:id
def get_site_team(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", None)
        league = event.get("queryStringParameters", {}).get("league", None)
        id = event.get("queryStringParameters", {}).get("id", None)
        if sport is None or league is None or id is None:
            return {"Message": "Missing sport, league, or team id parameter(s)"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams/{id}",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team by ID method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team (CORE API)
# GET /espn/core/team?sport=:sport&league=:league&year=:year&id=:id
def get_core_team(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", None)
        league = event.get("queryStringParameters", {}).get("league", None)
        year = event.get("queryStringParameters", {}).get("year", None)
        id = event.get("queryStringParameters", {}).get("id", None)
        if sport is None or league is None or year is None or id is None:
            return {"Message": "Missing sport, league, year, or team id parameter(s)"}, 400
        
        logger.info(f"Sending request to ESPN CORE API --> {ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/{year}/teams/{id}")

        response = http.request(
            "GET", 
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{id}",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team by ID method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get events for sport
# GET /espn/site/scoreboard
def get_site_scoreboard(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", "football")
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        week = event.get("queryStringParameters", {}).get("week", "")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/scoreboard?week={week}",
        )
        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Events method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get events for sport
# GET /espn/cdn/scoreboard
def get_cdn_scoreboard(event, logger):
    try:
        league = event.get("queryStringParameters", {}).get("league", "college-football")
        limit = event.get("queryStringParameters", {}).get("limit", 10)
        if league is None:
            return {"Message": "League parameter is required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_CDN_URL}/core/{league}/scoreboard?xhr=1&limit={limit}",
        )
        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Events method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get player info
# GET espn/athlete?sport=:sport&league=:league&id=:id
def get_athlete(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", None)
        league = event.get("queryStringParameters", {}).get("league", None)
        id = event.get("queryStringParameters", {}).get("id", None)
        if sport is None or league is None or id is None:
            return {"Message": "Missing sport, league, or athlete id parameter(s)"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{id}",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Player by ID method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get CDN Schedule
def get_cdn_schedule(event, logger):
    try:
        year = event.get("queryStringParameters", {}).get("year", None)
        week = event.get("queryStringParameters", {}).get("week", None)

        if year is None or week is None:
            return {"Message": "year and week parameters are required"}, 400

        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/schedule?year={year}&week={week}&xhr=1",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get CDN Schedule method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Site Standings
def get_site_standings(event, logger):
    try:
        sport = event.get("queryStringParameters", {}).get("sport", None)
        league = event.get("queryStringParameters", {}).get("league", None)
        season = event.get("queryStringParameters", {}).get("season", None)

        if sport is None or league is None or season is None:
            return {"Message": "sport, league and season parameters are required"}, 400

        response = http.request(
            "GET",
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/standings?season={season}",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Site Schedule method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get CDN Standings
def get_cdn_standings(event, logger):
    try:
        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/standings?xhr=1",
        )

        print("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get CDN Standings method !!")
        logger.exception(e)
        return json.dumps("Server error")
    

# Get Conference Standings
def get_conference_standings(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        season = params.get("season", None)
        season_type = params.get("season_type", None)
        id = params.get("id", None)

        if sport is None or league is None or season is None or season_type is None or id is None:
            return {"Message": "sport, league, season, season_type, and id parameters are required"}, 400

        response = http.request(
            "GET",
            f"{ESPN_SPORTS_URL}/v2/sports/football/leagues/nfl/seasons/{season}/types/{season_type}/groups/{id}/standings"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Conference Standings method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Roster
def get_team_roster(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        id = params.get("id", None)

        if sport is None or league is None or id is None:
            return { "Message": "sport, league, or id is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams/{id}/roster"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body

    except Exception as e:
        logger.exception("Exception in Get Team Roster !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get Team Schedule
def get_team_schedule(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        id = params.get("id", None)

        if sport is None or league is None or id is None:
            return { "Message": "sport, league, or id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams/{id}/schedule"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Schedule !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Injuries
def get_team_injuries(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        id = params.get("id", None)

        if sport is None or league is None or id is None:
            return { "Message": "sport, league, or id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/teams/{id}/injuries"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Injuries !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Depth Chart
def get_team_depth_chart(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        year = params.get("yr", None)
        id = params.get("id", None)

        if sport is None or league is None or year is None or id is None:
            return { "Message": "sport, league, or id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{id}/depthcharts"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Depth Chart !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Overview
def get_athlete_overview(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        ath_id = params.get("ath_id", None)

        if sport is None or league is None or ath_id is None:
            return { "Message": "sport, league, or athlete id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/nfl/{league}/{ath_id}/overview"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Overview !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Gamelog
def get_athlete_gamelog(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        ath_id = params.get("ath_id", None)

        if sport is None or league is None or ath_id is None:
            return { "Message": "sport, league, or athlete id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{ath_id}/gamelog"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Gamelog !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Eventlog
def get_athlete_eventlog(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        year = params.get("yr", None)
        ath_id = params.get("ath_id", None)

        if sport is None or league is None or year is None or ath_id is None:
            return { "Message": "sport, league, or athlete id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{football}/leagues/{league}/seasons/{year}/athletes/{ath_id}/eventlog"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Eventlog !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Splits
def get_athlete_splits(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        ath_id = params.get("ath_id", None)

        if sport is None or league is None or ath_id is None:
            return { "Message": "sport, league, or athlete id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{ath_id}/splits"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Splits !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Summary
def get_game_summary(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)

        if sport is None or league is None or event_id is None:
            return { "Message": "sport, league, or event id is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Summary !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Boxscore
def get_game_boxscore(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        event_id = params.get("event_id", None)

        if event_id is None:
            return { "Message": "Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_CDN_URL}/core/nfl/boxscore?xhr=1&gameId={event_id}"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Boxscore !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Play-by-Play
def get_game_playbyplay(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        event_id = params.get("event_id", None)

        if event_id is None:
            return { "Message": "Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_CDN_URL}/core/nfl/playbyplay?xhr=1&gameId={event_id}"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Play-by-Play !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Plays
def get_game_plays(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)
        limit = params.get("limit", "")

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{event_id}/plays?limit={limit}"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Plays !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Drives
def get_game_drives(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{event_id}/drives"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Drives !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Leaders
def get_site_leaders(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)
        season = params.get("season", "")
        season_type = params.get("seasonType", "")

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_URL}/apis/site/v3/sports/{sport}/{league}/leaders?season={season}&seasonType={season_type}"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Site Leaders !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Leaders (Core API)
def get_core_leaders(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)
        season = params.get("season", "")
        season_type = params.get("seasonType", "")

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{season}/types/{season_type}/leaders"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Core Leaders !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Draft
def get_draft(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        season = params.get("season", "")

        if sport is None or league is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{season}/draft"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Draft !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team News
def get_team_news(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        team_id = params.get("team_id", None)

        if sport is None or league is None or team_id is None:
            return { "Message": "Sport, League, or Team ID is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/news"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team News !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Specific Nights
def get_specific_nights(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        night = params.get("night", None)

        if night is None:
            return { "Message": "Night is required." }, 400

        response = http.request(
            "GET",
            "f{ESPN_SITE_URL}/apis/site/v2/{night}nightfootball"
        )

        logger.info("Response Code:", response.status)
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Specific Nights !!")
        logger.exception(e)
        return json.dumps("Server error")