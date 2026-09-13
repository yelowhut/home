-- FRENCH LANGUAGE LOCALIZATION

-- GUI
-- First item, title
ZO_CreateStringId("SI_SURVEYZONELIST_LIST_TITLE",  "Survey Zone List")

-- Keybinds
-- Toggle GUI
ZO_CreateStringId("SI_BINDING_NAME_SURVEYZONELIST_TOGGLE", "Afficher/Cacher la fenêtre")

-- Settings
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_LOCKUI", "Verrouiller l'interface")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAYED_WITH_WM", "Afficher avec la map")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_SURVEY", "Afficher la zone lorsqu'il n'y a que des repérages")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_TREASURE", "Afficher la zone lorsqu'il n'y a que des cartes aux trésors")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CURRENT_ZONE_FIRST", "Garder la zone actuelle en premier")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ITEM_TEXT_FORMAT", "Format du texte pour chaque zone")
ZO_CreateStringId(
    "SI_SURVEYZONELIST_SETTINGS_ITEM_TEXT_FORMAT_DESC",
    "Vous pouvez utiliser les raccourcis suivant dans le format du texte, ils seront remplacé par la valeur correspondante :\n"
    .."<<1>> Le nom de la zone\n"
    .."<<2>> Le nombre de répérage unique dans la zone\n"
    .."<<3>> Le nombre total de repérage dans la zone\n"
    .."<<4>> Le nombre de cartes aux trésors dans la zone\n"
    .."<<5>> Le nombre de repérage unique en banque\n"
    .."<<6>> Le nombre total de repérage en banque\n"
    .."<<7>> Le nombre de cartes aux trésors en banque\n"
    .."<<8>> Le nombre de repérage unique, sac et banque\n"
    .."<<9>> Le nombre total de repérage, sac et banque\n"
    .."<<10>> Le nombre de cartes aux trésors, sac et banque\n\n"
    .."La valeur par défaut est <<1>> : <<2>> - <<3>> / <<4>>"
)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_TITLE", "tri")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_DESC", "Vous pouvez définir l'ordre de priorité utilisé pour le tri de la liste des zones.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_ZONE_NAME", "Nom de la zone")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_SURVEY_NB_UNIQUE", "Nombre unique de repérage")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_SURVEY_NB_TOTAL", "Nombre total de répérage")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_SORT_TREASURE_NB_UNIQUE", "Nombre de carte aux trésors")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_TITLE", "Alertes")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_DESC", "Vous pouvez définir plusieurs types d'alerte qui se déclancheront lorsque vous serez sur le dernier spot d'un repérage")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN", "Quand lancer l'alerte")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN_START", "Sur le 1er point de ressource")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_WHEN_END", "Sur le dernier point de ressource")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_USE_ALERT", "Afficher une alerte à l'écran")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_USE_SOUND", "Jouer un son")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_CHOICE_SOUND", "Choix du son")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ALERT_PLAY_SOUND", "Jouer le son choisi")

-- GUI
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_REMAINING", "<<1>> restant")
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_GO_NEXT_SPOT", "Spot suivant")
ZO_CreateStringId("SI_SURVEYZONELIST_GUI_GO_NEXT_ZONE", "Zone suivante")

-- Spot - Notify
ZO_CreateStringId("SI_SURVEYZONELIST_SPOT_NOTIFY_LASTSPOT", "C'est le dernier repérage ici")

-- Collect
SurveyZoneList.lang.collectFindName = {
    "carte au trésor d'(.*)",
    "carte au trésor de (.*)",
    "carte au trésor des (.*)",
    "carte au trésor du (.*)",
    ".*: (.*)",
}

SurveyZoneList.lang.surveyAction = {
    "Ramasser",
    "Extraire",
    "Couper"
}

SurveyZoneList.lang.nodeName = {
    -- couture & alchmie
    "luxuriant$",
    "luxuriante$",
    "^piège du fourreur$",
    "de peluche ", -- Apocrypha : "Tissu déchiré" / "Tissu de peluche déchiré"
    "débordante$", -- Apocrypha : "Besace d'herboriste" / "Besace d'herboriste débordante"

    -- enchantement
    "protéiforme$",

    -- joiallerie
    "^veine de .* riche$",

    -- forge
    "^minerai de .* riche$",

    -- travail du bois
    "de premier choix$"
}

-- Settings : Craft breakdown (issue #10)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT", "Afficher le détail par métier")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT_DESC", "Affiche une colonne par métier sur chaque ligne de zone, avec le nombre de relevés de ce métier.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH", "Largeur du texte de zone")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH_DESC", "Largeur réservée au texte de la zone. Le détail par métier s'ajoute à cette largeur.")

-- Settings : Bank (issue #12)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_TITLE", "Banque")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_DESC", "Le contenu de la banque peut être compté en plus du sac, pour savoir quoi retirer avant de partir.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ", "Lire aussi les relevés en banque")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ_DESC", "Compte les relevés et les cartes au trésor rangés dans la banque du compte. Les alertes et le compteur de nœuds continuent de n'utiliser que le sac.")

-- Settings : Champion points (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_TITLE", "Points champion")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_DESC", "Récolte abondante donne une chance de récolter des ressources supplémentaires, un relevé fait sans elle est donc en partie gaspillé.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN", "Avertir si Récolte abondante n'est pas équipée")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN_DESC", "Affiche une ligne d'avertissement dans la fenêtre tant que l'étoile champion Récolte abondante n'est pas achetée ou pas équipée.")

-- Settings : Zone detection (issue #14)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_TITLE", "Détection des zones")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_DESC", "LibTreasure connaît la vraie zone de chaque relevé, ce qui évite les zones en double que l'analyse du nom d'objet produisait.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE", "Utiliser LibTreasure pour détecter les zones")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE_DESC", "Quand LibTreasure ne connaît pas un objet, par exemple dans une zone toute neuve, le nom de l'objet est analysé à la place.")

-- GUI : Champion point warning (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_CP_WARNING", "Récolte abondante n'est pas équipée")

-- Collect : craft of a survey, used only when LibTreasure does not know the item
SurveyZoneList.lang.craftFindName = {
    blacksmith = {"forgeron"},
    clothier   = {"couturier", "tailleur"},
    woodworker = {"bois"},
    enchanter  = {"enchanteur"},
    alchemist  = {"alchimiste"},
    jewelry    = {"joaill"},
}

SurveyZoneList.lang.championPlentifulHarvest = "Récolte abondante"
