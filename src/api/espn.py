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
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", "football")
        league = params.get("league", "college-football")
        limit = params.get("limit", 100)
        page = params.get("page", 1)
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400
        
        response = http.request("GET", f"{ESPN_SPORTS_URL}/v3/sports/{sport}/{league}/athletes?limit={limit}&page={page}")
        logger.info(f"Response Code: {response.status}")

        data = json.loads(response.data)

        logger.info(f"Response Keys: {data.keys()}")
        logger.info(f"Response Pages: {data['pageCount']}")

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
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", "football")
        league = params.get("league", "college-football")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams",
        )

        logger.info(f"Response Code: {response.status}")
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
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        id = params.get("id", None)
        if sport is None or league is None or id is None:
            return {"Message": "Missing sport, league, or team id parameter(s)"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams/{id}",
        )

        logger.info(f"Response Code: {response.status}")
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
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        year = params.get("year", None)
        id = params.get("id", None)
        if sport is None or league is None or year is None or id is None:
            return {"Message": "Missing sport, league, year, or team id parameter(s)"}, 400
        
        logger.info(f"Sending request to ESPN CORE API --> {ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/{year}/teams/{id}")

        response = http.request(
            "GET", 
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{id}",
        )

        logger.info(f"Response Code: {response.status}")
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
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", "football")
        league = params.get("league", "college-football")
        week = params.get("week", "")
        if sport is None or league is None:
            return {"Message": "Sport and League parameters are required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/scoreboard?week={week}",
        )
        logger.info(f"Response Code: {response.status}")
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
        params = event.get("queryStringParameters", {})
        league = params.get("league", "college-football")
        limit = params.get("limit", 10)
        if league is None:
            return {"Message": "League parameter is required"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_CDN_URL}/core/{league}/scoreboard?xhr=1&limit={limit}",
        )
        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Events method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get player info
# GET /espn/athlete?sport=:sport&league=:league&id=:id
def get_athlete(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        id = params.get("id", None)
        if sport is None or league is None or id is None:
            return {"Message": "Missing sport, league, or athlete id parameter(s)"}, 400

        response = http.request(
            "GET", 
            f"{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{id}",
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Player by ID method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get CDN Schedule
# GET /espn/cdn/schedule
def get_cdn_schedule(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        year = params.get("year", None)
        week = params.get("week", None)

        if year is None or week is None:
            return {"Message": "year and week parameters are required"}, 400

        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/schedule?year={year}&week={week}&xhr=1",
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get CDN Schedule method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Site Standings
# GET /espn/site/standings
def get_site_standings(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        season = params.get("season", None)

        if sport is None or league is None or season is None:
            return {"Message": "sport, league and season parameters are required"}, 400

        response = http.request(
            "GET",
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/standings?season={season}",
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Site Schedule method !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get CDN Standings
# GET /espn/cdn/standings
def get_cdn_standings(event, logger):
    try:
        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/standings?xhr=1",
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get CDN Standings method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Conference Standings
# GET /espn/conference-standings?sport=football&league=nfl&season=2025&season_type=1&id=NFC
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
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{season}/types/{season_type}/groups/{id}/standings/0"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)
        return body
    
    except Exception as e:
        logger.exception("Exception in Get Conference Standings method !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Roster
# GET /espn/team/roster?sport=football&league=nfl&id=1
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

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body

    except Exception as e:
        logger.exception("Exception in Get Team Roster !!")
        logger.exception(e)
        return json.dumps("Server error")

# Get Team Schedule
# GET /espn/team/schedule?sport=football&league=nfl&id=1
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
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/teams/{id}/schedule"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Schedule !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Injuries
# GET /espn/team/injuries?sport=football&league=nfl&id=1
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
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/teams/{id}/injuries"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Injuries !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team Depth Chart
# GET /espn/team/depth-chart?sport=football&league=nfl&year=2025&id=1
def get_team_depth_chart(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        year = params.get("year", None)
        id = params.get("id", None)

        if sport is None or league is None or year is None or id is None:
            return { "Message": "sport, league, or id is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{year}/teams/{id}/depthcharts"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team Depth Chart !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Overview
# GET /espn/athlete/overview?sport=football&league=nfl&ath_id=4241389
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
            f"{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{ath_id}/overview"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Overview !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Gamelog
# GET /espn/athlete/gamelog?sport=football&league=nfl&ath_id=4241389
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
            f"{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{ath_id}/gamelog"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Gamelog !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Eventlog
# GET /espn/athlete/eventlog?sport=football&league=nfl&year=2025&ath_id=4241389
def get_athlete_eventlog(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        year = params.get("year", None)
        ath_id = params.get("ath_id", None)

        if sport is None or league is None or year is None or ath_id is None:
            return { "Message": "sport, league, or athlete id is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{year}/athletes/{ath_id}/eventlog"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Eventlog !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Athlete Splits
# GET /espn/athlete/splits?sport=football&league=nfl&ath_id=4241389
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
            f"{ESPN_SITE_WEB_URL}/apis/common/v3/sports/{sport}/{league}/athletes/{ath_id}/splits"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Athlete Splits !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Summary
# GET /espn/game/summary?sport=football&league=nfl&event_id=
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
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/summary?event={event_id}"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Summary !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Boxscore
# GET /espn/game/boxscore?event_id=
def get_game_boxscore(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        event_id = params.get("event_id", None)

        if event_id is None:
            return { "Message": "Event ID is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/boxscore?xhr=1&gameId={event_id}"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Boxscore !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Play-by-Play
# GET /espn/game/playbyplay?event_id=
def get_game_playbyplay(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        event_id = params.get("event_id", None)

        if event_id is None:
            return { "Message": "Event ID is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_CDN_URL}/core/nfl/playbyplay?xhr=1&gameId={event_id}"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Play-by-Play !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Plays
# GET /espn/game/plays?sport=football&league=nfl&event_id=&limit=10
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
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{event_id}/plays?limit={limit}"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Plays !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Game Drives
# GET /espn/game/drives?sport=football&league=nfl&event_id=
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
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/events/{event_id}/competitions/{event_id}/drives"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Game Drives !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Leaders
# GET /espn/site/leaders?sport=football&league=nfl&event_id&season=2025&season_type=1
def get_site_leaders(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)
        season = params.get("season", "")
        season_type = params.get("season_type", "")

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SITE_URL}/apis/site/v3/sports/{sport}/{league}/leaders?season={season}&seasontype={season_type}"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Site Leaders !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Leaders (Core API)
# GET /espn/core/leaders?sport=football&league=nfl&event_id&season=2025&season_type=1
def get_core_leaders(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        sport = params.get("sport", None)
        league = params.get("league", None)
        event_id = params.get("event_id", None)
        season = params.get("season", "")
        season_type = params.get("season_type", "")

        if sport is None or league is None or event_id is None:
            return { "Message": "Sport, League, or Event ID is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{season}/types/{season_type}/leaders"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Core Leaders !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Draft
# GET /espn/draft?sport=football&league=nfl&season=2025
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
            f"{ESPN_SPORTS_URL}/v2/sports/{sport}/leagues/{league}/seasons/{season}/draft"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Draft !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Team News
# GET /espn/team/news?sport=football&league=nfl&team_id=1
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
            f"{ESPN_SITE_URL}/apis/site/v2/sports/{sport}/{league}/news"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Team News !!")
        logger.exception(e)
        return json.dumps("Server error")
    
# Get Specific Nights
# GET /espn/specific/nights?night=monday
def get_specific_nights(event, logger):
    try:
        params = event.get("queryStringParameters", {})
        night = params.get("night", None)

        if night is None:
            return { "Message": "Night is required." }, 400

        response = http.request(
            "GET",
            f"{ESPN_SITE_URL}/apis/site/v2/{night}nightfootball"
        )

        logger.info(f"Response Code: {response.status}")
        body = json.loads(response.data)

        return body
    
    except Exception as e:
        logger.exception("Exception in Get Specific Nights !!")
        logger.exception(e)
        return json.dumps("Server error")