import PySimpleGUI as sg
import os
from fix_host_save import sav_to_json
from fix_host_save import apply_fix
import json
import os
import subprocess
import sys
from inspect import getsourcefile
from os.path import abspath

def main():
    sg.theme('Dark')   # Add a touch of color

    # Define the layout
    selectSaveFolderLayout = [
        [sg.Text("Please select the \"Level.sav\" file that should be updated:")],
        [sg.InputText(key="folder_path", enable_events=True), sg.FileBrowse(file_types=(("Save files", "*.sav"),))],
        # [sg.Text("", size=(30, 1), key="dynamic_text")],  # Dynamic text element

        [sg.Text("Select the old player account (this progress will me migrated):", key='text_oldplayer', visible=False)],
        [sg.Combo(values=["old player"], key='dropdown_oldplayer', enable_events=True, size=(None, 400), visible=False)],

        [sg.Text("Select the new player account (this progress will be lost):", key='text_newplayer', visible=False)],
        [sg.Combo(values=["new player"], key='dropdown_newplayer', enable_events=True, size=(None, 400), visible=False)],

        [sg.Button("Migrate", key='button_migrate', visible=False)],
        
        [sg.ProgressBar(100, orientation='h', size=(20, 20), key='progressbar')],
        [sg.Text("", key='progressbarText')],
    ]

    # Create the window
    window = sg.Window("Folder Selection", selectSaveFolderLayout)
    selected_file = None
    old_player_selection_index = None
    new_player_selection_index = None
    level_json = None
    players_json = None
    players = None
    
    # Event loop
    while True:
        event, values = window.read()        

        if event == sg.WIN_CLOSED or event == "Cancel":
            break

        print(event)

        if event == "folder_path" and values["folder_path"] != selected_file:
            selected_file = values["folder_path"]
            # print(os.path.join(os.path.dirname(selected_file), "Player"))
            if not os.path.exists(selected_file) or os.path.basename(selected_file) != "Level.sav":
                sg.popup(f"The selected folder dosn't cointain a \"Level.sav\" file! Make sure you selected the correct folder and try again.", text_color='lightcoral')
            elif not os.path.exists(os.path.join(os.path.dirname(selected_file), "Players")):
                sg.popup(f"The selected folder dosn't cointain a \"Player\" folder! Make sure you selected the correct folder and try again.", text_color='lightcoral')
            else:
                window['progressbarText'].update("Loading and Converting Save files...")
                window['progressbar'].update_bar(30)
                window.refresh()

                level_sav_path = selected_file
                level_json_path = level_sav_path + '.json'
                if os.path.exists(level_json_path):
                    os.remove(level_json_path)
                sav_to_json(level_sav_path, level_json_path)

                window['progressbarText'].update("Finished converting Level.sav to json! Reading...")
                window['progressbar'].update_bar(80)
                window.refresh()

                with open(level_json_path) as f:
                    level_json = json.load(f)

                window['progressbarText'].update("Loaded Json. Reading Players...")
                window['progressbar'].update_bar(90)
                window.refresh()

                players_json = list(filter(lambda v: "IsPlayer" in v["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"] and v["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["IsPlayer"]["value"], level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]))
                players = list(map(lambda v: f'{v["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["NickName"]["value"]} (Lvl.{ v["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"]["Level"]["value"] if "Level" in v["value"]["RawData"]["value"]["object"]["SaveParameter"]["value"] else "0"})', players_json))
                # print(players)

                window['dropdown_oldplayer'].update(values=players, visible=True)
                window['text_oldplayer'].update(visible=True)
                window['dropdown_newplayer'].update(values=players, visible=True)
                window['text_newplayer'].update(visible=True)
                window['button_migrate'].update(visible=True)
                window['progressbarText'].update("Finished loading. Please select players")
                window['progressbar'].update_bar(100)
                window.refresh()                
        
        if event == "dropdown_oldplayer":
            old_player_selection_index = players.index(values['dropdown_oldplayer'])
            # print(old_player_selection_index)
            # print(players_json[old_player_selection_index]["key"]["InstanceId"]["value"])

        if event == "dropdown_newplayer":
            new_player_selection_index = players.index(values['dropdown_newplayer'])
            # print(new_player_selection_index)
            # print(players_json[new_player_selection_index]["key"]["InstanceId"]["value"])

        if event == "button_migrate":
            if new_player_selection_index == None or old_player_selection_index == None or old_player_selection_index == new_player_selection_index:
                sg.popup(f"You need to select players and can't select the same player in both fields!", text_color='lightcoral')
            else:
                popup_return = sg.popup_ok_cancel(f"Are you sure you wan't to migrate {players[old_player_selection_index]} -> {players[new_player_selection_index]} (This player will lose its progress: {players[new_player_selection_index]}). Please make a backup before running! Make sure the server is not running!")
                if popup_return == "OK":
                    player_folder_path = os.path.join(os.path.dirname(selected_file), "Players")
                    new_player_guid = players_json[new_player_selection_index]["key"]["PlayerUId"]["value"].replace("-","").upper()
                    old_player_guid = players_json[old_player_selection_index]["key"]["PlayerUId"]["value"].replace("-","").upper()
                    window['progressbarText'].update("Migrating, this can take up to 10 Minutes (don't worry if this window freezes, let it run)...")
                    window['progressbar'].update_bar(50)
                    window.refresh()
                    apply_fix(level_json_path, level_json, os.path.join(player_folder_path, f"{new_player_guid}.sav"), os.path.join(player_folder_path, f"{old_player_guid}.sav"))   
                    window['progressbarText'].update("Finished!")
                    window['progressbar'].update_bar(100)
                    window.refresh()
                    sg.popup("Finished. Have fun! (This window will close automaticly)")
                    break

    # Close the window
    window.close()

    if os.path.exists(level_json_path):
        os.remove(level_json_path)

if __name__ == "__main__":
    main()
