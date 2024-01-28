import json
import os
import subprocess
import sys
from inspect import getsourcefile
from os.path import abspath

def main():
    if len(sys.argv) < 4:
        print('fix-host-save.py <save_path> <new_guid> <old_guid>')
        exit(1)
    
    # Warn the user about potential data loss.
    print('WARNING: Running this script WILL change your save files and could \
potentially corrupt your data. It is HIGHLY recommended that you make a backup \
of your save folder before continuing. Press enter if you would like to continue.')
    input('> ')
    
    palworld_save_tool_path = os.path.join(os.path.dirname(abspath(getsourcefile(lambda:0))), "lib", "palworld-save-tools", "convert.py")
    save_path = sys.argv[1]
    new_guid = sys.argv[2]
    old_guid = sys.argv[3]
    
    # Apply expected formatting for the GUID.
    old_guid_formatted = '{}-{}-{}-{}-{}'.format(old_guid[:8], old_guid[8:12], old_guid[12:16], old_guid[16:20], old_guid[20:]).lower()
    new_guid_formatted = '{}-{}-{}-{}-{}'.format(new_guid[:8], new_guid[8:12], new_guid[12:16], new_guid[16:20], new_guid[20:]).lower()
    
    level_sav_path = save_path + '/Level.sav'
    player_sav_path = save_path + '/Players/'+ old_guid + '.sav'
    new_sav_path = save_path + '/Players/' + new_guid + '.sav'
    level_json_path = level_sav_path + '.json'
    player_json_path = player_sav_path + '.json'
    player_new_json_path = new_sav_path + '.json'

    # uesave_path must point directly to the executable, not just the path it is located in.
    if not os.path.exists(palworld_save_tool_path) or not os.path.isfile(palworld_save_tool_path):
        print('ERROR: The given <palworld_save_tool_path> of "' + palworld_save_tool_path + '" is invalid. It must point directly to the python script. Try initing git submodules.')
        exit(1)
    
    # save_path must exist in order to use it.
    if not os.path.exists(save_path):
        print('ERROR: Your given <save_path> of "' + save_path + '" does not exist. Did you enter the correct path to your save folder?')
        exit(1)
    
    # The player needs to have created a character on the dedicated server and that save is used for this script.
    if not os.path.exists(new_sav_path):
        print('ERROR: Your player save does not exist. Did you enter the correct new GUID of your player? It should look like "8E910AC2000000000000000000000000".\nDid your player create their character with the provided save? Once they create their character, a file called "' + new_sav_path + '" should appear. Look back over the steps in the README on how to get your new GUID.')
        exit(1)
    
    # Convert save files to JSON so it is possible to edit them.
    print('Converting save files to JSON ...')   
    sav_to_json(palworld_save_tool_path, level_sav_path, level_json_path)
    sav_to_json(palworld_save_tool_path, player_sav_path, player_json_path)
    sav_to_json(palworld_save_tool_path, new_sav_path, player_new_json_path)
    print('Converted save files to JSON')
    
    # Parse our JSON files.
    print('Parsing JSON files ...')   
    with open(player_json_path) as f:
        player_json = json.load(f)
    with open(level_json_path) as f:
        level_json = json.load(f)
    with open(player_new_json_path) as f:
        player_new_json = json.load(f)
    print('JSON files have been parsed')   
    
    ### Replace all instances of the old GUID with the new GUID.
    print(f'Replacing the player guid {old_guid_formatted} with {new_guid_formatted} ... (this might take a while)')

    # Player data replacement.
    player_json["properties"]["SaveData"]["value"]["PlayerUId"]["value"] = new_guid_formatted
    player_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["PlayerUId"]["value"] = new_guid_formatted
    player_instance_id = player_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"]
    player_new_instance_id = player_new_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"]  
    
    # Level data replacement 
    characterSaveParameterMap = level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]
    i = 0
    while i < len(characterSaveParameterMap):
        saved_parameter = characterSaveParameterMap[i]

        #delete the newly created player
        if player_new_instance_id == saved_parameter["key"]["InstanceId"]["value"]:
            characterSaveParameterMap.pop(i)
            continue

        if player_instance_id == saved_parameter["key"]["InstanceId"]["value"]:
            level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"][i]["key"]["PlayerUId"]["value"] = new_guid_formatted
        
        # Fix player key guids
        # This will "delete" all catched pals
        # elif old_guid_formatted == saved_parameter["key"]["PlayerUId"]["value"]:
        #     level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"][i]["key"]["PlayerUId"]["value"] = default_guid_formatted # the new_guid_formatted also dosn't work
        #     print('player id fixed')
        
        # Fix pawl ownership.
        if "OwnerPlayerUId" in saved_parameter["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]:
            pal_owner_player_id = saved_parameter["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["OwnerPlayerUId"]["value"]
            if pal_owner_player_id == old_guid_formatted:
                level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"][i]["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["OwnerPlayerUId"]["value"] = new_guid_formatted

        if "OldOwnerPlayerUIds" in saved_parameter["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]:
            old_pal_owner_player_values = saved_parameter["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["OldOwnerPlayerUIds"]["value"]["values"]
            for ii in range(len(old_pal_owner_player_values)):
                if old_pal_owner_player_values[ii] == old_guid_formatted:
                    level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"][i]["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["OldOwnerPlayerUIds"]["value"]["values"][ii] = new_guid_formatted
        i = i + 1

    # Guild data replacement.
    i = 0
    while i < len(level_json["properties"]["worldSaveData"]["value"]["GroupSaveDataMap"]["value"]):
        group_id = level_json["properties"]["worldSaveData"]["value"]["GroupSaveDataMap"]["value"][i]
        
        # This is fixing the left click bug issue (https://github.com/JannikBirn/palworld-host-save-fix/issues/6)
        if "individual_character_handle_ids" in group_id["value"]["RawData"]["value"]:
           group_handle_ids =  group_id["value"]["RawData"]["value"]["individual_character_handle_ids"]
           for ii in range(len(group_handle_ids)):
               if group_id["value"]["RawData"]["value"]["individual_character_handle_ids"][ii]["instance_id"] == player_instance_id:
                  group_id["value"]["RawData"]["value"]["individual_character_handle_ids"][ii]["guid"] = new_guid_formatted

            # This will break the pick up functionallity
            #    if group_id["value"]["RawData"]["value"]["individual_character_handle_ids"][ii]["guid"] == old_guid_formatted:
            #       group_id["value"]["RawData"]["value"]["individual_character_handle_ids"][ii]["guid"] = new_guid_formatted

        if "admin_player_uid" in group_id["value"]["RawData"]["value"] and old_guid_formatted == group_id["value"]["RawData"]["value"]["admin_player_uid"]:
            group_id["value"]["RawData"]["value"]["admin_player_uid"] = new_guid_formatted
        
        if "players" in group_id["value"]["RawData"]["value"]:            
            for iii in range(len(group_id["value"]["RawData"]["value"]["players"])):
                # deleting newly created player group, because a old one should already exist
                if new_guid_formatted == group_id["value"]["RawData"]["value"]["players"][iii]["player_uid"]:
                    level_json["properties"]["worldSaveData"]["value"]["GroupSaveDataMap"]["value"].pop(i)
                    i = i -1
                    break
                
                # fixing the old player group
                elif old_guid_formatted == group_id["value"]["RawData"]["value"]["players"][iii]["player_uid"]:
                    group_id["value"]["RawData"]["value"]["players"][iii]["player_uid"] = new_guid_formatted 
        i = i + 1

    print('Fixed player guid!')
    
    # Dump modified data to JSON.
    print('Exporting JSON files ...')
    with open(player_json_path, 'w') as f:
        json.dump(player_json, f, indent=2)
    with open(level_json_path, 'w') as f:
        json.dump(level_json, f, indent=2)
    print('JSON files have been exported')
    
    # Convert our JSON files to save files.
    print('Converting JSON files to save files ...')
    json_to_sav(palworld_save_tool_path, level_json_path)
    json_to_sav(palworld_save_tool_path, player_json_path)
    print('Converted JSON files back to save files')
    
    # Clean up miscellaneous GVAS and JSON files which are no longer needed.
    os.remove(level_json_path)
    os.remove(player_json_path)
    os.remove(player_new_json_path)
    print('Miscellaneous files removed')
    
    # We must rename the patched save file from the old GUID to the new GUID for the server to recognize it.
    if os.path.exists(new_sav_path):
        os.remove(new_sav_path)
    os.rename(player_sav_path, new_sav_path)
    print('Fix has been applied! Have fun!')

def sav_to_json(palworld_save_tool_path, file, output_path):
    # Convert to json with palworld-save-tools
    # Run palworld-save-tools.py with the uncompressed file piped as stdin
    process = subprocess.run(palworld_save_tool_to_json_params(palworld_save_tool_path, file, output_path))
    # Check if the command was successful
    if process.returncode != 0:
        print(f'palworld-save-tools.py failed to convert {file} (return {process.returncode})')
        print(process.stdout.decode('utf-8'))
        print(process.stderr.decode('utf-8'))
        return
    print(f'File {file} converted to JSON successfully')

def json_to_sav(palworld_save_tool_path, file):
    # Convert the file back to binary
    sav_file = file.replace('.sav.json', '.sav')
    os.remove(sav_file)
    process = subprocess.run(palworld_save_tool_from_json_params(palworld_save_tool_path, file, sav_file))
    if process.returncode != 0:
        print(f'palworld-save-tools.py failed to convert {file} (return {process.returncode})')
        print(process.stdout.decode('utf-8'))
        print(process.stderr.decode('utf-8'))
        return  

def palworld_save_tool_to_json_params(palworld_save_tool_path, input_file, out_path):
    args = [
        'python',
        palworld_save_tool_path,
        input_file,
        '--to-json',
        '--output', out_path,
    ]
    return args

def palworld_save_tool_from_json_params(palworld_save_tool_path, input_file, output_file):
    args = [
        'python',
        palworld_save_tool_path,
        input_file,
        '--from-json',
        '--output', output_file,
    ]
    return args

if __name__ == "__main__":
    main()
