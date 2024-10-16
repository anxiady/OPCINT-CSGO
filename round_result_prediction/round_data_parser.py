from awpy.data import NAV
import json
import os
from awpy.parser import DemoParser
from tqdm import tqdm
import time

def getCallout(coordinates):
    map=NAV["de_dust2"]
    for num, row in map.items():
        if row['northWestX'] <= coordinates[0] <= row['southEastX'] and row['northWestY'] <= coordinates[1] <= row['southEastY']:
            return row['areaName']
    return "Failed"

def get_players(parsed_data,roundnum, tick, side):
    team_stats = {} #includes both dead and living players
    round_data = parsed_data["gameRounds"][roundnum-1]
    alive=0
    teamEqVal=0
    if side=="ctSide":
        frameSide="ct"
        killSide="CT"
    else:
        frameSide="t"
        killSide="T"
    # last_tick=0

    for player in round_data[side]["players"]:
        team_stats[player["steamID"]] = {
            "playerName": player["playerName"],
            "is_alive": True, #F
            "hp": 100, #F
            "armor": 0, #F
            "equipment_value": 0, #F
            "cash": 0,
            "cash_spend_this_round":0, #F
            "round_damage": 0,
            "primary_weapon": None, #F   #needs to look the data structure closer
            "secondary_weapon": None, #F  #needs to look the data structure closer
            "active_weapon_category": None, #F    #Active Weapon Category of Player (One of either Primary, Secondary, Knife),
            "grenades_left": 0, #F     #(int) Number of grenades held by player,
            "flashes_left": 0,   #F    #(int) Number of flashes held by player,
            "smokes_left": 0,    #F    #(int) Number of smokes held by player,
            "molotovs_left": 0,  #F    #(int) Number of molotovs held by player,
            "is_blinded": False, #F    #[BONUS] (bool) Whether the player is blinded,
            "is_ducking": False, #F    #[BONUS] (bool)  Whether the player is ducking,
            "is_scoped": False,  #F    #[BONUS] (bool) Whether the player is scoped,
            "has_helmet": False, #F    #(bool) Whether the player has a helmet, DELETE!!!
            "has_defuser": False, #F   # (bool) Whether the player has a defuser,
            "total_kills": None,       #F
            "round_kills": 0,    #F
            "total_deaths": None,      #F
            "lastKnownWeapon": None,        #F
            "lastKnownPosition": None,      #F
            "velocityX": None,          #The velocity at X direction
            "velocityY": None,          #The velocity at Y direction
            "velocityZ": None,          #The velocity at Z direction
            "viewX": None,              #The X direction of the player
            "viewY": None,              #The Y direction of the player
            "callout": None,
            "round_damage": 0,
            "average_damage_per_round": 0, #[SUPER SUPER BONUS] (int) Average amount of damage output from a player across all previous rounds,
            "survives_round": False, #F    #(bool) Whether the player survives the round,
            "time_of_death": 0, #time in ticks until player's death
            #Additional for dead players
            "person_killed_by": None, #F     #(string) name of player who killed this dead_player,
            "weapon_killed_by": None
        }

    for event in round_data["kills"]:
        if event["tick"] <= tick and event["attackerSide"] == killSide:
            team_stats[event["attackerSteamID"]]["round_kills"] += 1

        if event["tick"] <= tick and event["victimSide"] == killSide:
            team_stats[event["victimSteamID"]]["time_of_death"] = event["tick"]
            team_stats[event["victimSteamID"]]["person_killed_by"] = event["attackerName"]
            team_stats[event["victimSteamID"]]["weapon_killed_by"] = event["weapon"]

    for event in round_data["damages"]:
        if event["tick"] <= tick and event["attackerSide"] == killSide:
            team_stats[event["attackerSteamID"]]["round_damage"] += event["hpDamageTaken"]

    for frame in round_data["frames"]:
        if frame["tick"] <= tick:
            teamEqVal=frame[frameSide]["teamEqVal"]
            for player in frame[frameSide]["players"]:
                if player["steamID"] in team_stats:
                    team_stats[player["steamID"]]["lastKnownPosition"] = [player["x"],player["y"],player["z"]]
                    team_stats[player["steamID"]]["callout"] = getCallout([player["x"],player["y"],player["z"]])
                    team_stats[player["steamID"]]["lastKnownWeapon"] = [player["inventory"]][0]
                    team_stats[player["steamID"]]["hp"] = [player["hp"]][0]
                    team_stats[player["steamID"]]["is_alive"] = [player["isAlive"]][0]
                    team_stats[player["steamID"]]["survives_round"] = [player["isAlive"]][0]
                    team_stats[player["steamID"]]["armor"] = [player["armor"]][0]
                    team_stats[player["steamID"]]["equipment_value"] = [player["equipmentValue"]][0]
                    team_stats[player["steamID"]]["cash_spend_this_round"] = [player["cashSpendThisRound"]][0]
                    team_stats[player["steamID"]]["is_blinded"] = [player["isBlinded"]][0]
                    team_stats[player["steamID"]]["is_ducking"] = [player["isDucking"]][0]
                    team_stats[player["steamID"]]["is_scoped"] = [player["isScoped"]][0]
                    team_stats[player["steamID"]]["cash"] = [player["cash"]][0]
                    team_stats[player["steamID"]]["has_helmet"] = [player["hasHelmet"]][0]
                    team_stats[player["steamID"]]["has_defuser"] = [player["hasDefuse"]][0]
                    team_stats[player["steamID"]]["amount_spent"] = [player["cashSpendTotal"]][0]
                    team_stats[player["steamID"]]["active_weapon_category"] = [player["activeWeapon"]][0]
                    team_stats[player["steamID"]]["velocityX"] = [player["velocityX"]][0]
                    team_stats[player["steamID"]]["velocityY"] = [player["velocityY"]][0]
                    team_stats[player["steamID"]]["velocityZ"] = [player["velocityZ"]][0]
                    team_stats[player["steamID"]]["viewX"] = [player["viewX"]][0]
                    team_stats[player["steamID"]]["viewY"] = [player["viewY"]][0]
                    
                if player["isAlive"] and frame["tick"] == tick:
                    alive+=1
        else:
            #break the loop once the tick exceeds the specified tick
            break
    extraData={}
    extraData["team"]=team_stats
    living_players={}
    dead_players={}
    keys_toRemove=["person_killed_by", "weapon_killed_by", "amount_spent","lastKnownWeapon", "time_of_death"]
    keys_toKeep={"playerName", 
                 "person_killed_by", 
                 "weapon_killed_by",
                 "lastKnownPosition", 
                 "callout",
                 "amount_spent", 
                 "equipment_value", 
                 "cash_spend_this_round", 
                 "cash", 
                 "round_kills",
                 "total_kills",
                 "time_of_death", 
                 "round_damage",
                 "average_damage_per_round"}

    for id, stat_item in team_stats.items():
        if stat_item["is_alive"]:
            for weapon in stat_item["lastKnownWeapon"]:
                if weapon["weaponClass"]=="Pistols":
                    stat_item["secondary_weapon"]=weapon["weaponName"]
                if weapon["weaponClass"]=="Rifle":
                    stat_item["primary_weapon"]=weapon["weaponName"]
                if weapon["weaponClass"]=="SMG":
                    stat_item["primary_weapon"]=weapon["weaponName"]
                if weapon["weaponName"]=="HE Grenade":
                    stat_item["grenades_left"]=weapon["ammoInMagazine"]+weapon["ammoInReserve"]
                if weapon["weaponName"]=="Flashbang":
                    stat_item["flashes_left"]=weapon["ammoInMagazine"]+weapon["ammoInReserve"]
                if weapon["weaponName"]=="Smoke Grenade":
                    stat_item["smokes_left"]=weapon["ammoInMagazine"]+weapon["ammoInReserve"]
                if weapon["weaponName"]=="Molotov": ### !!! Needs to be tested to find the exact matching name
                    stat_item["molotovs_left"]=weapon["ammoInMagazine"]+weapon["ammoInReserve"]
            if stat_item["active_weapon_category"]==stat_item["primary_weapon"]:
                stat_item["active_weapon_category"]="Primary"
            elif stat_item["active_weapon_category"]==stat_item["secondary_weapon"]:
                stat_item["active_weapon_category"]="Secondary"
            else:
                stat_item["active_weapon_category"]="Knife"
                
            for key in keys_toRemove:
                if key in stat_item:
                    del stat_item[key]
            living_players[id]=stat_item
        else:
            for key in list(stat_item.keys()):
                if key not in keys_toKeep:
                    del stat_item[key]
            dead_players[id]=stat_item
    
    
    extraData["team_equipment_value"] = teamEqVal
    extraData["winner"] = round_data["winningSide"]
    return living_players, dead_players, extraData

def rounds_stats(demo_data):
    bomb_rounds=[]
    rounds_stats={}
    bombPosition=[]
    for round in demo_data["gameRounds"]:
        for bomb_event in round["bombEvents"]:
            if bomb_event["bombAction"]=="plant":
                bomb_rounds.append(round["roundNum"])
                bombPosition=[bomb_event['playerX'],bomb_event['playerY'],bomb_event['playerZ']]
        living_players, dead_players, extraData=get_players(demo_data,round["roundNum"], round["endTick"],"ctSide")  #The difference I found is that the officialend tick would clear cash spend this round
        living_players1, dead_players1, extraData1=get_players(demo_data,round["roundNum"], round["endTick"],"tSide")
        round_stat={
            "round_winner": round["winningSide"], #F   #(string) Team that wins the round ("CT_Team" or "T_Team"),
            "round_number": round["roundNum"], #F   #(int) Number of current round,
            "bomb_coordinates": bombPosition,     #F  not very sure whether to use bombposition in frames.
            "round_length": round["endOfficialTick"]-round["startTick"], #BONUS]
            "bomb_plant_time": round["bombPlantTick"], #[BONUS] 
            "ct_team": {
                "rounds_won": 0, #F  Should I include current round?
                "team_equipment_value": extraData["team_equipment_value"], #DO this while also check if bombpositions are the same from frames and bombevents
                "living_players": living_players,
                "dead_players": dead_players
            },
            "t_team":{
                "rounds_won": 0,#(int) Number of rounds team has already won,
                "team_equipment_value": extraData1["team_equipment_value"],#(int) See teamEqVal in frames,
                "living_players": living_players1,
                "dead_players": dead_players1
            },
            "winningSide": round["winningSide"]
        }
        rounds_stats[round["roundNum"]]=round_stat
    
    tWins=0
    ctWins=0
    totalKill={}
    totalDeath={}
    totalDamage={}
    totalRound=0
    avgDamage={}
    
    for id, value in extraData["team"].items():
        totalKill[id]=0
        totalDeath[id]=0
        totalDamage[id]=0
    for id, value in extraData1["team"].items():
        totalKill[id]=0
        totalDeath[id]=0
        totalDamage[id]=0
    for roundNum, round in rounds_stats.items():
        for ID, player in round["ct_team"]["living_players"].items():
            totalKill[ID]+=player["round_kills"]
            totalDamage[ID]+=player["round_damage"]
            
        for ID, player in round["ct_team"]["dead_players"].items():
            totalKill[ID]+=player["round_kills"]
            totalDeath[ID]+=1
            totalDamage[ID]+=player["round_damage"]
        for ID, player in round["t_team"]["living_players"].items():
            totalKill[ID]+=player["round_kills"]
            totalDamage[ID]+=player["round_damage"]
            
        for ID, player in round["t_team"]["dead_players"].items():
            totalKill[ID]+=player["round_kills"]
            totalDeath[ID]+=1
            totalDamage[ID]+=player["round_damage"]

        rounds_stats[roundNum]["ct_team"]["rounds_won"]=ctWins
        rounds_stats[roundNum]["t_team"]["rounds_won"]=tWins
        if round["winningSide"]=="T":
            tWins+=1
        if round["winningSide"]=="CT":
            ctWins+=1
        totalRound=roundNum
    
    for roundNum, round in rounds_stats.items():
        # print(roundNum)
        for ID, player in round["ct_team"]["living_players"].items():
            rounds_stats[roundNum]["ct_team"]["living_players"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["ct_team"]["living_players"][ID]["total_deaths"]=totalDeath[ID]
            rounds_stats[roundNum]["ct_team"]["living_players"][ID]["average_damage_per_round"]=totalDamage[ID]/totalRound
            avgDamage[ID]=totalDamage[ID]/totalRound
        for ID, player in round["t_team"]["living_players"].items():
            rounds_stats[roundNum]["t_team"]["living_players"][ID]["average_damage_per_round"]=totalDamage[ID]/totalRound
            rounds_stats[roundNum]["t_team"]["living_players"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["t_team"]["living_players"][ID]["total_deaths"]=totalDeath[ID]
            avgDamage[ID]=totalDamage[ID]/totalRound

        # To get rid of the round number key
        statHolder=[]
        for id, stat in rounds_stats[roundNum]["ct_team"]["living_players"].items():
            statHolder.append(stat)
        rounds_stats[roundNum]["ct_team"]["living_players"]=statHolder
        statHolder=[]
        for id, stat in rounds_stats[roundNum]["ct_team"]["dead_players"].items():
            statHolder.append(stat)
        rounds_stats[roundNum]["ct_team"]["dead_players"]=statHolder
        statHolder=[]
        for id, stat in rounds_stats[roundNum]["t_team"]["living_players"].items():
            statHolder.append(stat)
        rounds_stats[roundNum]["t_team"]["living_players"]=statHolder
        statHolder=[]
        for id, stat in rounds_stats[roundNum]["t_team"]["dead_players"].items():
            statHolder.append(stat)
        rounds_stats[roundNum]["t_team"]["dead_players"]=statHolder
    total=[totalDeath, totalKill, avgDamage]
    for key in list(rounds_stats.keys()):
        if key not in bomb_rounds:
            del rounds_stats[key]
    return rounds_stats, total, bomb_rounds

def timestamp(parsed_data, roundnum):
    plant_tick=[]
    site=""
    for bomb_event in parsed_data["gameRounds"][roundnum]["bombEvents"]:
        if bomb_event["bombAction"]=="plant":
            plant_tick.append(bomb_event["tick"])
            plant_tick.append(bomb_event["bombSite"])

    return plant_tick

def getPrompt(demo_data, roundNum, total):
    bombTick=timestamp(demo_data, roundNum-1)[0]
    bombSite=timestamp(demo_data, roundNum-1)[1]
    tlive, tdead, textra=get_players(demo_data, roundNum, bombTick, "tSide")
    ctlive, ctdead, ctextra=get_players(demo_data, roundNum, bombTick, "ctSide")

    t={}
    ct={}

    for ID, player in tlive.items():
        tlive[ID]["total_kills"]=total[1][ID]
        tlive[ID]["total_deaths"]=total[0][ID]
        tlive[ID]["average_damage_per_round"]=total[2][ID]
    for ID, player in tdead.items():
        tdead[ID]["total_kills"]=total[1][ID]
        tdead[ID]["total_deaths"]=total[0][ID]
        tdead[ID]["average_damage_per_round"]=total[2][ID]
    for ID, player in ctlive.items():
        ctlive[ID]["total_kills"]=total[1][ID]
        ctlive[ID]["total_deaths"]=total[0][ID]
        ctlive[ID]["average_damage_per_round"]=total[2][ID]
    for ID, player in ctdead.items():
        ctdead[ID]["total_kills"]=total[1][ID]
        ctdead[ID]["total_deaths"]=total[0][ID]
        ctdead[ID]["average_damage_per_round"]=total[2][ID]
    
    statHolder=[]
    for id, stat in ctlive.items():
        statHolder.append(stat)
    ct["living_players"]=statHolder
    statHolder=[]
    for id, stat in ctdead.items():
        statHolder.append(stat)
    ct["dead_players"]=statHolder
    statHolder=[]
    for id, stat in tlive.items():
        statHolder.append(stat)
    t["living_players"]=statHolder
    statHolder=[]
    for id, stat in tdead.items():
        statHolder.append(stat)
    t["dead_players"]=statHolder

    team_stat={}
    team_stat['T']=t
    team_stat['CT']=ct
    team_stat['winner']=textra['winner']
    team_stat['bombSite']=bombSite
    round_stat={}
    round_stat[roundNum]=team_stat

    return round_stat

all_data = []
start_time = time.time()
script_directory = os.getcwd()

def clean_up_json_files():
    for file in os.listdir(script_directory):
        if file.endswith('.json'):
            os.remove(os.path.join(script_directory, file))


### Replace with the right directory path ###
directory = 'Your Directory'
for filename in tqdm(os.listdir(directory), desc="Processing files"):
    if filename.endswith('.dem'):
        demo_path = os.path.join(directory, filename)
        try:
            demo_parser = DemoParser(demofile=demo_path, parse_rate=1)
            parsed_data = demo_parser.parse()
            stats, total, bomb_rounds = rounds_stats(parsed_data)
            ordered= {"original_demo": f"{filename}"}
            for roundnum in bomb_rounds:
                ordered.update(getPrompt(parsed_data,roundnum, total))
            all_data.append(ordered)
        except Exception as e:
            error_message=str(e)
            print(e)
            if "panic" in error_message:
                error_message = {"error": "panic", "original_demo": f"{filename}"}
            else:
                error_message = {"error": "error set", "original_demo": f"{filename}"}
            all_data.append(error_message)
    clean_up_json_files()
with open(f'rouund_data.json', 'w') as json_file:
    json.dump(all_data, json_file, indent=4)

print("--- %s seconds ---" % (time.time() - start_time))
