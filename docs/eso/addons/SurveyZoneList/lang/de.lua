-- GERMAN LANGUAGE LOCALIZATION

-- Collect
SurveyZoneList.lang.collectFindName = {
    ".*: (.*)",
}

SurveyZoneList.lang.surveyAction = {
    "Hacken",
    "Nehmen",
    "Abbauen",
    "Sammeln"
}

SurveyZoneList.lang.nodeName = {
    "^hervorragendes",
    "^buschige",
    "plüschfetzen$", --Apocrypha : "Zerrissener Stoff" / "Zerrissener Plüschfetzen"
    "^reichhaltiges",
    "^kürschnerfalle$",
    "^proteischer",
    "^prall gefüllter" -- Apocrypha : "Beutel eines Kräuterkundigen" / "Prall gefüllter Beutel eines Kräuterkundigen"

    -- bois
    -- Survey : [03:16] Hacken / Hervorragendes Rubineschenholz
    -- Normal : [03:23] Hacken / Rubinesche

    -- enchantement
    -- survey : [03:53] Nehmen / Proteischer Runenstein
    -- normal : [03:19] Nehmen / Runenstein

    -- couture
    -- survey : [03:47] Sammeln / Kürschnerfalle
    --          [03:47] Nehmen / Buschige Ahnenseide
    -- normal : [03:21] Nehmen / Ahnenseide

    -- alchimie
    -- survey : [03:32] Nehmen / Buschige Bergblume
    -- normal : [03:22] Nehmen / Bergblume

    -- forge
    -- survey : [03:43] Abbauen / Reichhaltiges Rubediterz
    -- normal : [03:21] Abbauen / Rubediterz

    -- joaillerie
    -- survey : [03:52] Abbauen / Reichhaltiges Platinflöz
    -- normal : [03:26] Abbauen / Platinflöz
}

-- Settings : Craft breakdown (issue #10)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT", "Aufschlüsselung nach Handwerk anzeigen")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_DISPLAY_CRAFT_DESC", "Zeigt pro Zonenzeile eine Spalte je Handwerk mit der Anzahl der Vermessungen dieses Handwerks.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH", "Breite des Zonentextes")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_TEXT_WIDTH_DESC", "Für den Zonentext reservierte Breite. Die Handwerksspalten kommen dazu.")

-- Settings : Bank (issue #12)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_TITLE", "Bank")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_DESC", "Der Bankinhalt kann zusätzlich zum Rucksack gezählt werden, damit klar ist, was vor dem Aufbruch zu entnehmen ist.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ", "Vermessungen auch in der Bank lesen")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_BANK_READ_DESC", "Zählt die Vermessungen und Schatzkarten in der Kontobank mit. Warnungen und der Knotenzähler nutzen weiterhin nur den Rucksack.")

-- Settings : Champion points (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_TITLE", "Championpunkte")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_DESC", "Reiche Ernte gibt eine Chance auf zusätzliche Rohstoffe, eine Vermessung ohne sie ist also teilweise verschenkt.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN", "Warnen, wenn Reiche Ernte nicht belegt ist")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_CP_WARN_DESC", "Zeigt eine Warnzeile im Fenster, solange der Championstern Reiche Ernte nicht gekauft oder nicht belegt ist.")

-- Settings : Zone detection (issue #14)
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_TITLE", "Zonenerkennung")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_DESC", "LibTreasure kennt die echte Zone jeder Vermessung und vermeidet so die doppelten Zonen, die das Auslesen des Gegenstandsnamens erzeugt hat.")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE", "LibTreasure zur Zonenerkennung nutzen")
ZO_CreateStringId("SI_SURVEYZONELIST_SETTINGS_ZONE_LIBTREASURE_DESC", "Kennt LibTreasure einen Gegenstand nicht, etwa in einer brandneuen Zone, wird stattdessen der Gegenstandsname ausgelesen.")

-- GUI : Champion point warning (issue #13)
ZO_CreateStringId("SI_SURVEYZONELIST_CP_WARNING", "Reiche Ernte ist nicht belegt")

-- Collect : craft of a survey, used only when LibTreasure does not know the item
SurveyZoneList.lang.craftFindName = {
    blacksmith = {"schmied"},
    clothier   = {"schneider"},
    woodworker = {"schreiner", "holz"},
    enchanter  = {"verzauber"},
    alchemist  = {"alchemist"},
    jewelry    = {"juwelier"},
}

SurveyZoneList.lang.championPlentifulHarvest = "Reiche Ernte"
