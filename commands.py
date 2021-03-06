# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

"""
KodiDevKit is a plugin to assist with Kodi skinning / scripting using Sublime Text 3
"""

import re
import webbrowser
import platform
import os
import logging
from lxml import etree as ET

import sublime
import sublime_plugin

from .libs import utils
from .libs.kodi import kodi

import subprocess

APP_NAME = "Kodi"
SETTINGS_FILE = 'kodidevkit.sublime-settings'
SUBLIME_PATH = utils.get_sublime_path()


class OpenKodiLogCommand(sublime_plugin.WindowCommand):

    """
    open kodi log from its default location
    """

    def run(self):
        filename = "%s.log" % APP_NAME.lower()
        self.log = utils.check_paths([os.path.join(kodi.userdata_folder, filename),
                                      os.path.join(kodi.userdata_folder, "temp", filename),
                                      os.path.join(os.path.expanduser("~"), "Library", "Logs", filename)])
        self.window.open_file(self.log)


class OpenAltKodiLogCommand(sublime_plugin.WindowCommand):

    """
    open alternative kodi log from its default location
    (visible for windows portable mode)
    """

    def visible(self):
        return platform.system() == "Windows" and self.settings.get("portable_mode")

    def run(self):
        filename = "%s.log" % APP_NAME.lower()
        self.log = os.path.join(os.getenv('APPDATA'), APP_NAME, filename)
        self.window.open_file(self.log)


class OpenSourceFromLog(sublime_plugin.TextCommand):

    """
    open file from exception description and jump to according place in code
    """

    def run(self, edit):
        for region in self.view.sel():
            if not region.empty():
                self.view.insert(edit, region.begin(), self.view.substr(region))
                continue
            line_contents = self.view.substr(self.view.line(region))
            match = re.search(r'File "(.*?)", line (\d*), in .*', line_contents)
            if match:
                sublime.active_window().open_file("{}:{}".format(os.path.realpath(match.group(1)),
                                                                 match.group(2)),
                                                  sublime.ENCODED_POSITION)
                return
            match = re.search(r"', \('(.*?)', (\d+), (\d+), ", line_contents)
            if match:
                sublime.active_window().open_file("{}:{}:{}".format(os.path.realpath(match.group(1)),
                                                                    match.group(2),
                                                                    match.group(3)),
                                                  sublime.ENCODED_POSITION)
                return


class GoToOnlineHelpCommand(sublime_plugin.TextCommand):

    """
    open browser and go to wiki page
    """

    CONTROLS = {"group": "http://kodi.wiki/view/Group_Control",
                "grouplist": "http://kodi.wiki/view/Group_List_Control",
                "label": "http://kodi.wiki/view/Label_Control",
                "fadelabel": "http://kodi.wiki/view/Fade_Label_Control",
                "image": "http://kodi.wiki/view/Image_Control",
                "largeimage": "http://kodi.wiki/view/Large_Image_Control",
                "multiimage": "http://kodi.wiki/view/MultiImage_Control",
                "button": "http://kodi.wiki/view/Button_control",
                "radiobutton": "http://kodi.wiki/view/Radio_button_control",
                "selectbutton": "http://kodi.wiki/view/Group_Control",
                "togglebutton": "http://kodi.wiki/view/Toggle_button_control",
                "multiselect": "http://kodi.wiki/view/Multiselect_control",
                "spincontrol": "http://kodi.wiki/view/Spin_Control",
                "spincontrolex": "http://kodi.wiki/view/Settings_Spin_Control",
                "progress": "http://kodi.wiki/view/Progress_Control",
                "list": "http://kodi.wiki/view/List_Container",
                "wraplist": "http://kodi.wiki/view/Wrap_List_Container",
                "fixedlist": "http://kodi.wiki/view/Fixed_List_Container",
                "panel": "http://kodi.wiki/view/Text_Box",
                "rss": "http://kodi.wiki/view/RSS_feed_Control",
                "visualisation": "http://kodi.wiki/view/Visualisation_Control",
                "videowindow": "http://kodi.wiki/view/Video_Control",
                "edit": "http://kodi.wiki/view/Edit_Control",
                "epggrid": "http://kodi.wiki/view/EPGGrid_control",
                "mover": "http://kodi.wiki/view/Mover_Control",
                "resize": "http://kodi.wiki/view/Resize_Control"
                }

    def is_visible(self):
        region = self.view.sel()[0]
        line_contents = self.view.substr(self.view.line(region))
        scope_name = self.view.scope_name(region.b)
        return "text.xml" in scope_name and "<control " in line_contents

    def run(self, edit):
        region = self.view.sel()[0]
        line = self.view.line(region)
        line_contents = self.view.substr(line)
        try:
            root = ET.fromstring(line_contents + "</control>")
            control_type = root.attrib["type"]
            self.go_to_help(control_type)
        except Exception:
            logging.info("error when trying to open from %s" % line_contents)

    def go_to_help(self, word):
        """
        open browser and go to wiki page for control with type *word
        """
        webbrowser.open_new(self.CONTROLS[word])


class AppendTextCommand(sublime_plugin.TextCommand):

    """
    append a line of text to the current view
    """

    def run(self, edit, label):
        self.view.insert(edit, self.view.size(), label + "\n")


class LogCommand(sublime_plugin.TextCommand):

    """
    log text into a text panel
    """

    def run(self, edit, label, panel_name='example'):
        if not hasattr(self, "output_view"):
            self.output_view = self.view.window().create_output_panel(panel_name)
        self.output_view.insert(edit, self.output_view.size(), label + '\n')
        self.output_view.show(self.output_view.size())
        self.view.window().run_command("show_panel", {"panel": "output." + panel_name})


class CreateElementRowCommand(sublime_plugin.WindowCommand):

    """
    Creates duplicates based on a template defined by current text selection
    Show input panel for user to enter number of items to generate,
    then execute ReplaceXmlElementsCommand
    """

    def run(self):
        self.window.show_input_panel("Enter number of items to generate",
                                     "1",
                                     on_done=self.generate_items,
                                     on_change=None,
                                     on_cancel=None)

    def generate_items(self, num_items):
        self.window.run_command("replace_xml_elements", {"num_items": num_items})


class ReplaceXmlElementsCommand(sublime_plugin.TextCommand):

    """
    Create *num_items duplicates based on template defined by current text selection
    """

    def run(self, edit, num_items):
        if not num_items.isdigit():
            return None
        selected_text = self.view.substr(self.view.sel()[0])
        text = ""
        reg = re.search(r"\[(-?[0-9]+)\]", selected_text)
        offset = int(reg.group(1)) if reg else 0
        for i in range(int(num_items)):
            text = text + selected_text.replace("[%i]" % offset, str(i + offset)) + "\n"
            i += 1
        for region in self.view.sel():
            self.view.replace(edit, region, text)
            break


class EvaluateMathExpressionPromptCommand(sublime_plugin.WindowCommand):

    """
    Allows calculations for currently selected regions
    Shows an input panel so user can enter equation, then execute EvaluateMathExpressionCommand
    """

    def run(self):
        self.window.show_input_panel("Write Equation (x = selected int)",
                                     "x",
                                     self.evaluate,
                                     None,
                                     None)

    def evaluate(self, equation):
        self.window.run_command("evaluate_math_expression", {'equation': equation})


class EvaluateMathExpressionCommand(sublime_plugin.TextCommand):

    """
    Change currently selected regions based on *equation
    """

    def run(self, edit, equation):
        for i, region in enumerate(self.view.sel()):
            text = self.view.substr(region)
            temp_equation = equation.replace("i", str(i))
            if text.replace('-', '').isdigit():
                temp_equation = temp_equation.replace("x", text)
            self.view.replace(edit, region, str(eval(temp_equation)).replace(".0", ""))


class ColorPickerCommand(sublime_plugin.WindowCommand):

    """
    Launch ColorPicker, return kodi-formatted color string
    """

    def is_visible(self):
        settings = sublime.load_settings('KodiColorPicker.sublime-settings')
        settings.set('color_pick_return', None)
        self.window.run_command('color_pick_api_is_available',
                                {'settings': 'KodiColorPicker.sublime-settings'})
        return bool(settings.get('color_pick_return', False))

    def run(self):
        settings = sublime.load_settings('KodiColorPicker.sublime-settings')
        settings.set('color_pick_return', None)
        self.window.run_command('color_pick_api_get_color',
                                {'settings': 'KodiColorPicker.sublime-settings',
                                 'default_color': '#ff0000'})
        color = settings.get('color_pick_return')
        if color:
            self.window.active_view().run_command("insert",
                                                  {"characters": "FF" + color[1:]})


class SetKodiFolderCommand(sublime_plugin.WindowCommand):

    """
    Show input panel to set kodi folder, set default value according to OS
    """

    def run(self):
        if sublime.platform() == "linux":
            preset_path = "/usr/share/%s/" % APP_NAME.lower()
        elif sublime.platform() == "windows":
            preset_path = "C:/%s/" % APP_NAME.lower()
        elif platform.system() == "Darwin":
            preset_path = os.path.join(os.path.expanduser("~"),
                                       "Applications",
                                       "%s.app" % APP_NAME,
                                       "Contents",
                                       "Resources",
                                       APP_NAME)
        else:
            preset_path = ""
        self.window.show_input_panel("Set Kodi folder",
                                     preset_path,
                                     self.set_kodi_folder,
                                     None,
                                     None)

    @staticmethod
    def set_kodi_folder(path):
        """
        Sets kodi path to *path and saves it if file exists.
        """
        if os.path.exists(path):
            sublime.load_settings(SETTINGS_FILE).set("kodi_path", path)
            sublime.save_settings(SETTINGS_FILE)
        else:
            logging.critical("Folder %s does not exist." % path)


class ExecuteBuiltinPromptCommand(sublime_plugin.WindowCommand):

    """
    Shows an input dialog, then triggers ExecuteBuiltinCommand
    """

    def run(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        self.window.show_input_panel("Execute builtin",
                                     self.settings.get("prev_json_builtin", ""),
                                     self.execute_builtin,
                                     None,
                                     None)

    def execute_builtin(self, builtin):
        self.settings.set("prev_json_builtin", builtin)
        self.window.run_command("execute_builtin", {"builtin": builtin})


class ExecuteBuiltinCommand(sublime_plugin.WindowCommand):

    """
    Sends json request to execute a builtin using script.toolbox
    """

    def run(self, builtin):
        params = {"addonid": "script.toolbox",
                  "params": {"info": "builtin",
                             "id": builtin}}
        kodi.request_async(method="Addons.ExecuteAddon",
                           params=params)


class GetInfoLabelsPromptCommand(sublime_plugin.WindowCommand):

    """
    Displays the values of chosen infolabels via output panel
    User chooses infolabels via input panel
    """

    def run(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        self.window.show_input_panel("Get InfoLabels (comma-separated)",
                                     self.settings.get("prev_infolabel", ""),
                                     self.show_info_label,
                                     None,
                                     None)

    @utils.run_async
    def show_info_label(self, label_string):
        """
        fetch infolabel with name *label_string from kodi via json and display it.
        """
        self.settings.set("prev_infolabel", label_string)
        words = label_string.split(",")
        logging.warning("send request...")
        result = kodi.request(method="XBMC.GetInfoLabels",
                              params={"labels": words})
        if result:
            logging.warning("Got result:")
            _, value = result["result"].popitem()
            logging.warning(str(value))


class BrowseKodiVfsCommand(sublime_plugin.WindowCommand):

    """
    Allows to browse the Kodi VFS via JSON-RPC
    """

    def run(self):
        self.nodes = [["video", "library://video"],
                      ["music", "library://music"]]
        self.window.show_quick_panel(items=self.nodes,
                                     on_select=self.on_done,
                                     selected_index=0)

    @utils.run_async
    def on_done(self, index):
        if index == -1:
            return None
        node = self.nodes[index]
        data = kodi.request(method="Files.GetDirectory",
                            params={"directory": node[1], "media": "files"})
        self.nodes = [[item["label"], item["file"]] for item in data["result"]["files"]]
        self.window.show_quick_panel(items=self.nodes,
                                     on_select=self.on_done,
                                     selected_index=0)


class GetInfoBooleansPromptCommand(sublime_plugin.WindowCommand):

    """
    Displays the values of chosen booleans via output panel
    User chooses booleans via input panel
    """

    def run(self):
        self.settings = sublime.load_settings(SETTINGS_FILE)
        self.window.show_input_panel("Get boolean values (comma-separated)",
                                     self.settings.get("prev_boolean", ""),
                                     self.resolve_kodi_condition,
                                     None,
                                     None)

    @utils.run_async
    def resolve_kodi_condition(self, condition):
        """
        show OutputPanel with kodi JSON result for b
        """
        self.settings.set("prev_boolean", condition)
        words = condition.split(",")
        logging.warning("send request...")
        result = kodi.request(method="XBMC.GetInfoBooleans",
                              params={"booleans": words})
        if result:
            logging.warning("Got result:")
            _, value = result["result"].popitem()
            logging.warning(str(value))


class OpenKodiAddonCommand(sublime_plugin.WindowCommand):

    """
    Open another SublimeText instance containing the chosen addon
    """

    def run(self):
        self.nodes = kodi.get_userdata_addons()
        self.window.show_quick_panel(items=self.nodes,
                                     on_select=self.on_done,
                                     selected_index=0)

    def on_done(self, index):
        if index == -1:
            return None
        path = os.path.join(kodi.userdata_folder, "addons", self.nodes[index])
        subprocess.Popen([SUBLIME_PATH, "-n", "-a", path])
