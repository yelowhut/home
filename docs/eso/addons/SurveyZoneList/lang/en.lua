-- ENGLISH LANGUAGE LOCALIZATION

-- GUI
-- First item, title
ZO_CreateStringId("SI_SURVEYZONELIST_LIST_TITLE",  "Survey Zone List")

-- Keybinds
-- Toggle GUI
ZO_CreateStringId("SI_BINDING_NAME_SURVEYZONELIST_TOGGLE", "Toggle window")

-- Settings
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_LOCKUI", "Lock UI")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAYED_WITH_WM", "Displayed with the world map")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_SURVEY", "Display the zone when they are only survey")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_TREASURE", "Display the zone when they are only treasure map")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CURRENT_ZONE_FIRST", "Keep the current zone first")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ITEM_TEXT_FORMAT", "Text format used for each zone")
ZO_CreateStringId(
    "SI_SURVEYZONELIST_SETTINGS_ITEM_TEXT_FORMAT_DESC",
    "You can use the following placeholders in the text format, which will be replaced with the value information :\n"
    .."<<1>> Zone's name\n"
    .."<<2>> Number of unique survey in the zone\n"
    .."<<3>> Total number of survey in the zone\n"
    .."<<4>> Number of treasure map in the zone\n"
    .."<<5>> Number of unique survey in the bank\n"
    .."<<6>> Total number of survey in the bank\n"
    .."<<7>> Number of treasure map in the bank\n"
    .."<<8>> Number of unique survey, bag and bank\n"
    .."<<9>> Total number of survey, bag and bank\n"
    .."<<10>> Number of treasure map, bag and bank\n\n"
    .."Default value is <<1>> : <<2>> - <<3>> / <<4>>"
)
-- Settings : Sort
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_TITLE", "Sort")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_DESC", "You can define the order priority used to sort the zone list.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_ZONE_NAME", "zone name")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_SURVEY_NB_UNIQUE", "number of unique survey")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_SURVEY_NB_TOTAL", "total number of survey")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_TREASURE_NB_UNIQUE", "number of treasure map")
-- Settings : Interaction
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_INTERACTION_TITLE", "Interaction")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_INTERACTION_DESC", "Action to do when you can interact with a survey's node")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_INTERACTION_SHOW_ICON", "Display a craft icon on survey's node")
-- Settings : Alert
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_TITLE", "Alerts")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_DESC", "You can define some alert's type when you are on the last survey's spot")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN", "When do the alert")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN_START", "On the first node")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN_END", "On the last node")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_USE_ALERT", "Display an alert on the screen")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_USE_SOUND", "Play a sound")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_CHOICE_SOUND", "Sound choice")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_PLAY_SOUND", "Play the chosen sound")

-- GUI
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_REMAINING", "<<1>> remaining")
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_GO_NEXT_SPOT", "next spot")
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_GO_NEXT_ZONE", "next zone")

-- Spot - Notify
ZO_CreateStringId("SI_SURVEYZONELIST_SPOT_NOTIFY_LASTSPOT", "It's the last survey here")

-- Collect
SurveyZoneList.lang.collectFindName = {
    "(.*) treasure map",
    ".*: (.*)",
}

SurveyZoneList.lang.surveyAction = {
    "Cut",
    "Collect",
    "Mine"
}

SurveyZoneList.lang.nodeName = {
    -- clothier & alchemist (couture & alchimie)
    "^bulging", -- Apocrypha : "Herbalist's Satchel" / "Bulging Herbalist's Satchel"
    "^lush",
    "^plush", -- Apocrypha : "Torn Cloth" / "Plush Torn Cloth"
    "^furrier's trap$",

    -- Enchanting (enchantement)
    "^protean",

    -- Jewelry & blacksmith (joaillerie & forge)
    "^rich",

    -- Woodworking (travail du bois)
    "^pristine"
}

-- Settings : Craft breakdown (issue #10)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT", "Display the craft breakdown")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT_DESC", "Show one column per craft on each zone row, with the number of surveys of that craft.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH", "Width of the zone text")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH_DESC", "Width reserved for the zone text. The craft breakdown is added on top of it.")

-- Settings : Bank (issue #12)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_TITLE", "Bank")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_DESC", "The bank content can be counted alongside your backpack, so you know what to withdraw before leaving.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ", "Also read surveys in the bank")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ_DESC", "Count the surveys and treasure maps stored in the account bank. Alerts and the node counter keep using your backpack only.")

-- Settings : Champion points (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_TITLE", "Champion points")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_DESC", "Plentiful Harvest gives a chance to gather extra resources, so a survey run without it is partly wasted.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN", "Warn when Plentiful Harvest is not slotted")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN_DESC", "Display a warning line in the window while the Plentiful Harvest champion star is not bought or not slotted.")

-- Settings : Zone detection (issue #14)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_TITLE", "Zone detection")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_DESC", "LibTreasure knows the real zone of every survey, which avoids the duplicated zones the item name parser used to create.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE", "Use LibTreasure to detect zones")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE_DESC", "When LibTreasure does not know an item, for example in a brand new zone, the item name is parsed instead.")

-- GUI : Champion point warning (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_CP_WARNING", "Plentiful Harvest is not slotted")

-- Collect : craft of a survey, used only when LibTreasure does not know the item
SurveyZoneList.lang.craftFindName = {
    blacksmith = {"blacksmith"},
    clothier   = {"clothier"},
    woodworker = {"woodworker"},
    enchanter  = {"enchanter"},
    alchemist  = {"alchemist"},
    jewelry    = {"jewelry"},
}

SurveyZoneList.lang.championPlentifulHarvest = "Plentiful Harvest"
