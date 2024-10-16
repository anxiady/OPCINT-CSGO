from awpy.data import NAV
import json
import random
import os
from awpy.parser import DemoParser
from tqdm import tqdm
import time
import traceback

def getCallout(coordinates):
    map=NAV["de_dust2"]
    for num, row in map.items():
        if row['northWestX'] <= coordinates[0] <= row['southEastX'] and row['northWestY'] <= coordinates[1] <= row['southEastY']:
            return row['areaName']
    return "Failed"

def rounds_stats(demo_data, tick, round_num):
    bomb_rounds=[]
    rounds_stats={}
    bombPosition=[]
    for round in demo_data["gameRounds"]:
        roundNum=round["roundNum"]-1
        if roundNum < round_num:
            living_players, dead_players, extraData=get_players(demo_data,roundNum, round["endTick"],"ctSide")
            living_players1, dead_players1, extraData1=get_players(demo_data,roundNum, round["endTick"],"tSide")

            round_stat={
                "winningSide": round["winningSide"],
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
                }
            }
            rounds_stats[roundNum]=round_stat
            
        elif roundNum == round_num:
            living_players, dead_players, extraData=get_players(demo_data,roundNum, tick,"ctSide")
            living_players1, dead_players1, extraData1=get_players(demo_data,roundNum, tick,"tSide")
            round_stat={
                "winningSide": round["winningSide"],
                "ct_team": {
                    "rounds_won": 0, #F  Should I include current round?
                    "team_equipment_value": extraData["team_equipment_value"], #DO this while also check if bombpositions are the same fr>
                    "living_players": living_players,
                    "dead_players": dead_players
                },
                "t_team":{
                    "rounds_won": 0,#(int) Number of rounds team has already won,
                    "team_equipment_value": extraData1["team_equipment_value"],#(int) See teamEqVal in frames,
                    "living_players": living_players1,
                    "dead_players": dead_players1
                }
            }
            rounds_stats[roundNum]=round_stat
    
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
        for ID, player in round["ct_team"]["living_players"].items():
            rounds_stats[roundNum]["ct_team"]["living_players"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["ct_team"]["living_players"][ID]["total_deaths"]=totalDeath[ID]
            avgDamage[ID]=totalDamage[ID]/(round_num+1)
        for ID, player in round["t_team"]["living_players"].items():
            rounds_stats[roundNum]["t_team"]["living_players"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["t_team"]["living_players"][ID]["total_deaths"]=totalDeath[ID]
            avgDamage[ID]=totalDamage[ID]/(round_num+1)

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
    # total=[totalDeath, totalKill]
    total=[totalDeath, totalKill, avgDamage]
    for key in list(rounds_stats.keys()):
        if key not in bomb_rounds:
            del rounds_stats[key]

    return rounds_stats, total, bomb_rounds, living_players, living_players1

def timestamp(parsed_data, roundnum):
    kills_tick=[]
    tick_rate=parsed_data["gameRounds"][roundnum]["kills"][0]['tick']/parsed_data["gameRounds"][roundnum]["kills"][0]['seconds']
    for kill in parsed_data["gameRounds"][roundnum]["kills"]:
        kills_tick.append(kill['tick'])

    return kills_tick, tick_rate

def is_alive(parsed_data, roundNum, tick, ID):
    round_data = parsed_data["gameRounds"][roundnum-1]
    for frame in round_data["frames"]:
        if frame["tick"] <= tick:
            for player in frame[frameSide]["players"]:
                if player["isAlive"]:
                    return True
                else:
                    return False
        else:
            return "Out of Frames"

def getEndPlayers(parsed_data,roundnum, tick, side):
    team_stats = {} #includes both dead and living players
    round_data = parsed_data["gameRounds"][roundnum]
    if side=="ctSide":
        frameSide="ct"
        killSide="CT"
    else:
        frameSide="t"
        killSide="T"
    for player in round_data[side]["players"]:
        team_stats[player["steamID"]] = {
            "playerName": player["playerName"],
            "side": frameSide,
            "is_alive": True,
            "hp": 100, #F
            "armor": 0, #F
            "equipment_value": 0, #F
            "cash": 0,
            "cash_spend_this_round":0, #F
            "round_damage": 0,
            "total_kills": None,       #F
            "round_kills": 0,    #F
            "total_deaths": None,      #F
            "round_damage": 0,
            "average_damage_per_round": 0, #[SUPER SUPER BONUS] (int) Average amount of damage output from a player across all previous rounds,
        }

    for event in round_data["kills"]:
        if event["tick"] <= tick and event["attackerSide"] == killSide:
            team_stats[event["attackerSteamID"]]["round_kills"] += 1

    for event in round_data["damages"]:
        if event["tick"] <= tick and event["attackerSide"] == killSide:
            team_stats[event["attackerSteamID"]]["round_damage"] += event["hpDamageTaken"]

    for frame in round_data["frames"]:
        if frame["tick"] <= tick:
            for player in frame[frameSide]["players"]:
                if player["steamID"] in team_stats:
                    team_stats[player["steamID"]]["hp"] = [player["hp"]][0]
                    team_stats[player["steamID"]]["is_alive"] = [player["isAlive"]][0]
                    team_stats[player["steamID"]]["armor"] = [player["armor"]][0]
                    team_stats[player["steamID"]]["equipment_value"] = [player["equipmentValue"]][0]
                    team_stats[player["steamID"]]["cash_spend_this_round"] = [player["cashSpendThisRound"]][0]
                    team_stats[player["steamID"]]["cash"] = [player["cash"]][0]
                    team_stats[player["steamID"]]["amount_spent"] = [player["cashSpendTotal"]][0]
        else:
            break
    
    return team_stats

def getTotal(demo_data):
    rounds_stats={}
    for i in range(len(demo_data['gameRounds'])):
        for round in demo_data["gameRounds"]:
            # print(f"rounds_stats: {round['roundNum']} and {round_num}")
            roundNum=round["roundNum"]-1
            ct=getEndPlayers(demo_data,roundNum, round["endTick"],"ctSide")
            t=getEndPlayers(demo_data,roundNum, round["endTick"],"tSide")
            rounds_stats[roundNum]={'ct':ct , 't':t}
            
    totalKill={}
    totalDeath={}
    totalDamage={}
    totalRound=0

    avgDamage={}
    
    for id, value in ct.items():
        totalKill[id]=0
        totalDeath[id]=0
        totalDamage[id]=0
    for id, value in t.items():
        totalKill[id]=0
        totalDeath[id]=0
        totalDamage[id]=0
    for roundNum, round in rounds_stats.items():
        for ID, player in round["ct"].items():
            if not player['is_alive']:
                totalDeath[ID]+=1
            totalKill[ID]+=player["round_kills"]
            totalDamage[ID]+=player["round_damage"]
            rounds_stats[roundNum]["ct"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["ct"][ID]["total_deaths"]=totalDeath[ID]
            avgDamage[ID]=totalDamage[ID]/(roundNum+1)
            rounds_stats[roundNum]["ct"][ID]["average_damage_per_round"]=avgDamage[ID]

        for ID, player in round["t"].items():
            if not player['is_alive']:
                totalDeath[ID]+=1
            totalKill[ID]+=player["round_kills"]
            totalDamage[ID]+=player["round_damage"]
            rounds_stats[roundNum]["t"][ID]["total_kills"]=totalKill[ID]
            rounds_stats[roundNum]["t"][ID]["total_deaths"]=totalDeath[ID]
            avgDamage[ID]=totalDamage[ID]/(roundNum+1)
            rounds_stats[roundNum]["t"][ID]["average_damage_per_round"]=avgDamage[ID]

    return rounds_stats

def sample_without_intervals(total_range, excluded_intervals, sample_size):
    allowed_numbers = set(total_range)
    for start, end in excluded_intervals:
        allowed_numbers.difference_update(range(start, end + 1))
    allowed_numbers = list(allowed_numbers)
    return random.sample(allowed_numbers, sample_size)

def get_false_label(parsed_data,roundnum, tick, side, random_tick):
    team_stats = {} #includes both dead and living players
    round_data = parsed_data["gameRounds"][roundnum]
    alive=0
    teamEqVal=0
    non_dead_list=[]  #to record players who hasn't been dead within the range
    if side=="ctSide":
        frameSide="ct"
        killSide="CT"
    else:
        frameSide="t"
        killSide="T"
    for player in round_data[side]["players"]:
        non_dead_list.append(player["steamID"])
        team_stats[player["steamID"]] = {
            "playerName": player["playerName"],
            "side": frameSide,
            "tick": tick,
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
        if tick <= frame["tick"] <= (tick+random_tick):
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

                if not player["isAlive"] and player["steamID"] in non_dead_list:
                    non_dead_list.remove(player["steamID"])
    if len(non_dead_list)==0:
        return None,None,None
    elif len(non_dead_list)==1:
        team_stats[non_dead_list[0]]["will_die"]=0
    else:
        team_stats[non_dead_list[random.randint(0,len(non_dead_list)-1)]]["will_die"]=0  #pick a random player out of all the qualified ones
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
            "average_damage_per_round",
            "side",
            "tick",
            "hp",
            "is_alive"}

    for id, stat_item in team_stats.items():
        if stat_item["is_alive"]:
            if stat_item["lastKnownWeapon"]:
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

def getPrompt(demo_data, roundNum, total):
    tick_rate = demo_data['tickRate']
    tick_values = [second * tick_rate for second in range(3, 16)]
    statHolder=[]
    for i in range(15):
        random_tick = random.choice(tick_values)
        start = int(demo_data["gameRounds"][roundNum]["startTick"])
        end = int(demo_data["gameRounds"][roundNum]["endTick"]-random_tick)
        random_start = random.randint(start, end)
        # print(f"start: {start}")
        # print(f"end: {end}")
        tlive, tdead, textra=get_false_label(demo_data, roundNum, random_start, "tSide", random_tick)
        while not tlive:    # in case if all players are invalid
            random_start = random.randint(start, end)
            tlive, tdead, textra=get_false_label(demo_data, roundNum, random_start, "tSide", random_tick)
        ctlive, ctdead, textra=get_false_label(demo_data, roundNum, random_start, "ctSide", random_tick)
        
        while not ctlive:
            random_start = random.randint(start, end)
            ctlive, ctdead, textra=get_false_label(demo_data, roundNum, random_start, "ctSide", random_tick)
            
        for ID, player in tlive.items():
            tlive[ID]["total_kills"]=total[roundNum]["t"][ID]["total_kills"]
            tlive[ID]["total_deaths"]=total[roundNum]["t"][ID]["total_deaths"]
            tlive[ID]["average_damage_per_round"]=total[roundNum]["t"][ID]["average_damage_per_round"]
            statHolder.append(player)
        for ID, player in tdead.items():
            tdead[ID]["total_kills"]=total[roundNum]["t"][ID]["total_kills"]
            tdead[ID]["total_deaths"]=total[roundNum]["t"][ID]["total_deaths"]
            tdead[ID]["average_damage_per_round"]=total[roundNum]["t"][ID]["average_damage_per_round"]
            statHolder.append(player)
        for ID, player in ctlive.items():
            ctlive[ID]["total_kills"]=total[roundNum]["ct"][ID]["total_kills"]
            ctlive[ID]["total_deaths"]=total[roundNum]["ct"][ID]["total_deaths"]
            ctlive[ID]["average_damage_per_round"]=total[roundNum]["ct"][ID]["average_damage_per_round"]     
            statHolder.append(player)
        for ID, player in ctdead.items():
            ctdead[ID]["total_kills"]=total[roundNum]["ct"][ID]["total_kills"]
            ctdead[ID]["total_deaths"]=total[roundNum]["ct"][ID]["total_deaths"]
            ctdead[ID]["average_damage_per_round"]=total[roundNum]["ct"][ID]["average_damage_per_round"]
            statHolder.append(player)
    return statHolder

all_data = []
start_time = time.time()
script_directory = os.getcwd()

def clean_up_json_files():
    for file in os.listdir(script_directory):
        if file.endswith('.json'):
            os.remove(os.path.join(script_directory, file))
def isNotNone(parsed_data):
    round_data = parsed_data["gameRounds"][0]
    if round_data['ctSide']['players'] is None:
        return False
    else:
        return True
        

### Replace with the right directory path ###
directory = 'Your Directory'

for filename in tqdm(os.listdir(directory), desc="Processing files"):
    if filename.endswith('.dem'):
        demo_path = os.path.join(directory, filename)
        try:
            demo_parser = DemoParser(demofile=demo_path, parse_rate=1)
            parsed_data = demo_parser.parse()
            if isNotNone(parsed_data):
                total=getTotal(parsed_data)
                for i in range(len(parsed_data['gameRounds'])):    #start at 0
                    if len(parsed_data["gameRounds"][i]["kills"]) > 1:
                        all_data.append({i : getPrompt(parsed_data,i,total)})
            else:
                all_data.append({"error": "None", "original_demo": f"{filename}"})
        except Exception as e:
            error_message=str(e)
            print(e)
            traceback_details = traceback.format_exc()
            print(traceback_details)
            if "panic" in error_message:
                error_message = {"error": "panic", "original_demo": f"{filename}"}
            else:
                error_message = {"error": "error set", "original_demo": f"{filename}"}
            all_data.append(error_message)
    clean_up_json_files()

with open('false_label_data.json', 'w') as json_file:
    json.dump(all_data, json_file, indent=4)

print("--- %s seconds ---" % (time.time() - start_time))
